terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Pub/Sub topics
resource "google_pubsub_topic" "signal_messages" {
  name = "signal-messages"
}

resource "google_pubsub_topic" "stock_requests" {
  name = "stock-requests"
}

resource "google_pubsub_topic" "response_queue" {
  name = "response-queue"
}

# Firestore database (already exists in most projects)
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  # Prevent destruction of existing database
  lifecycle {
    prevent_destroy = true
  }
}

# Service account for Cloud Functions
resource "google_service_account" "signal_bot" {
  account_id   = "signal-bot"
  display_name = "Signal Bot Service Account"
  description  = "Service account for Signal bot Cloud Functions"
}

# IAM roles for the service account
resource "google_project_iam_member" "signal_bot_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.signal_bot.email}"
}

resource "google_project_iam_member" "signal_bot_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.signal_bot.email}"
}

resource "google_project_iam_member" "signal_bot_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.signal_bot.email}"
}

resource "google_project_iam_member" "signal_bot_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.signal_bot.email}"
}

# Cloud Storage bucket for function source code
resource "google_storage_bucket" "function_source" {
  name     = "${var.project_id}-signal-bot-functions"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Cloud Storage bucket for Signal configurations
resource "google_storage_bucket" "signal_configs" {
  name     = "${var.project_id}-signal-configs"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# Webhook Cloud Function
resource "google_cloudfunctions2_function" "webhook" {
  name     = "signal-webhook"
  location = var.region

  build_config {
    runtime     = "python311"
    entry_point = "signal_webhook"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = "webhook-source.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "256M"
    timeout_seconds    = 60

    service_account_email = google_service_account.signal_bot.email

    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GCP_REGION          = var.region
    }
  }

  depends_on = [
    google_pubsub_topic.signal_messages
  ]
}

# Message Processor Cloud Function
resource "google_cloudfunctions2_function" "message_processor" {
  name     = "message-processor"
  location = var.region

  build_config {
    runtime     = "python311"
    entry_point = "process_message"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = "message-processor-source.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "256M"
    timeout_seconds    = 60

    service_account_email = google_service_account.signal_bot.email

    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GCP_REGION          = var.region
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type           = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic         = google_pubsub_topic.signal_messages.id
    retry_policy         = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_pubsub_topic.signal_messages,
    google_pubsub_topic.stock_requests
  ]
}

# Stock Handler Cloud Function
resource "google_cloudfunctions2_function" "stock_handler" {
  name     = "stock-handler"
  location = var.region

  build_config {
    runtime     = "python311"
    entry_point = "handle_stock_request"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = "stock-handler-source.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "512M"
    timeout_seconds    = 120

    service_account_email = google_service_account.signal_bot.email

    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GCP_REGION          = var.region
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type           = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic         = google_pubsub_topic.stock_requests.id
    retry_policy         = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_pubsub_topic.stock_requests
  ]
}

# Signal Registration Cloud Function
resource "google_cloudfunctions2_function" "signal_registration" {
  name     = "signal-registration"
  location = var.region

  build_config {
    runtime     = "python311"
    entry_point = "signal_registration"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = "signal-registration-source.zip"
      }
    }
  }

  service_config {
    max_instance_count = 3
    available_memory   = "512M"
    timeout_seconds    = 180

    service_account_email = google_service_account.signal_bot.email

    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GCP_REGION          = var.region
    }
  }

  depends_on = [
    google_storage_bucket.signal_configs
  ]
}

# Signal Sender Cloud Function
resource "google_cloudfunctions2_function" "signal_sender" {
  name     = "signal-sender"
  location = var.region

  build_config {
    runtime     = "python311"
    entry_point = "signal_sender"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = "signal-sender-source.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "512M"
    timeout_seconds    = 120

    service_account_email = google_service_account.signal_bot.email

    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GCP_REGION          = var.region
    }
  }

  depends_on = [
    google_storage_bucket.signal_configs
  ]
}

# Cloud Function invoker permissions for webhook
resource "google_cloudfunctions2_function_iam_member" "webhook_invoker" {
  project        = var.project_id
  location       = var.region
  cloud_function = google_cloudfunctions2_function.webhook.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Cloud Function invoker permissions for Signal registration
resource "google_cloudfunctions2_function_iam_member" "signal_registration_invoker" {
  project        = var.project_id
  location       = var.region
  cloud_function = google_cloudfunctions2_function.signal_registration.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Cloud Function invoker permissions for Signal sender
resource "google_cloudfunctions2_function_iam_member" "signal_sender_invoker" {
  project        = var.project_id
  location       = var.region
  cloud_function = google_cloudfunctions2_function.signal_sender.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Secret Manager secrets
resource "google_secret_manager_secret" "signal_phone_number" {
  secret_id = "signal-phone-number"

  replication {
    auto {}
  }
}