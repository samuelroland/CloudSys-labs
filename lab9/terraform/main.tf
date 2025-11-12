terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "app_server" {
  ami           = "ami-0149b2da6ceec4bb0" # Ubuntu Server 20.04 LTS (HVM), SSD Volume Type
  instance_type = "t2.micro"

  tags = {
    Name   = "ExampleAppServerInstance"
    Course = "TSM-CloudSys"
    Year   = "2025"
    Lab    = "Terraform"
    Group  = "D"
  }
}
