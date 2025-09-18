output "webhook_url" {
  description = "URL for the Signal webhook"
  value       = google_cloudfunctions2_function.webhook.service_config[0].uri
}

output "signal_registration_url" {
  description = "URL for Signal registration function"
  value       = google_cloudfunctions2_function.signal_registration.service_config[0].uri
}

output "signal_sender_url" {
  description = "URL for Signal sender function"
  value       = google_cloudfunctions2_function.signal_sender.service_config[0].uri
}

output "project_id" {
  description = "Google Cloud Project ID"
  value       = var.project_id
}

output "pubsub_topics" {
  description = "Created Pub/Sub topics"
  value = {
    signal_messages = google_pubsub_topic.signal_messages.name
    stock_requests  = google_pubsub_topic.stock_requests.name
    response_queue  = google_pubsub_topic.response_queue.name
  }
}

output "service_account_email" {
  description = "Service account email for the Signal bot"
  value       = google_service_account.signal_bot.email
}