// Variables to use accross the project
// which can be accessed by var.project_id
variable "project_id" {
  description = "The project ID to host the cluster in"
  default     = "robusto-ai-dev-490114"
}

variable "region" {
  description = "The region the cluster in"
  default     = "us-central1"
}

variable "zone" {
  description = "The region the cluster in"
  default     = "us-central1-a"
}

variable "bucket" {
  description = "GCS bucket for MLE course"
  default     = "mle-course101"
}

variable "ssh_keys" {
  default = "vominhtri:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDGKhwwXfHVtJoqOI9z1/66I54g+era+HGfrcQVNHSzlvMOZolWTh0ZVs/CRB52WyFSrfxfhy8nwxIknEy5Hzt4YgShxel66AdlEC6yc42GtPra46MxojiZlMA/lc4ZT4DXwaMYY3AbnJSGwTFT3c0gAz7tLfa3QnpSzht+3hVB5itr+43Wn6Bn/+np6dSy4LO6iHv8R/GgfVwxK+o/yYnOCt7oEfmX4uLOnzxPAgH1kYQf/aW326U+7Pju56fMJjPJ0u0GiAyZbW0zSwD4NWiX/doCt0cKxxU1PrwfLyc259E2wUQ6af4eLaiwQMCq569lAIEYE8UTE3XyXHK1ZftGtcAdEiTPTCJtZCJoyHkHi+t7jLgwdD5DcqyvRiEyCsvTiDRzWLsUfABfN04BIcNt8oAJrF/USh6ldk8PmyVxu077bICpurOd8XGGXdoPo0S+3rmUYOCXonsHAhzz7lNAfbtUR9mgzD6XdFTzZbTZK0gstKB/eYLf52rSRMqSUnTmQCTobr0NfrZ3Gx54UzLSure/2HBDgB+kDi/iykLpDYfus3WGd/frKehwY+/V6k4hjpcTrVqiyK9Q202kc8OwV4Tp5f6/iFkcgE5E3s4eZHUfqh79PCDfdLn5Vc2KDKHmR2yZe0ozSbKF1H7l50bnFbq6n2DWCGw5wyIqYgbZWw== vominhtri"
}

variable "firewall_name" {
  description = "Name of firewall"
  default     = "allow-jelkins-port"
}

variable "disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 50
}

variable "image" {
  description = "OS image for the VM"
  type        = string
  default     = "projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20230727"
}