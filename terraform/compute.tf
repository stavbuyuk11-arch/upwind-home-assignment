data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "app_code" {
  bucket        = "upwind-phishing-app-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_object" "app_py" {
  bucket = aws_s3_bucket.app_code.id
  key    = "app.py"
  source = "../app.py"
  etag   = filemd5("../app.py")
}

resource "aws_s3_object" "director_py" {
  bucket = aws_s3_bucket.app_code.id
  key    = "director.py"
  source = "../director.py"
  etag   = filemd5("../director.py")
}

resource "aws_s3_object" "index_html" {
  bucket = aws_s3_bucket.app_code.id
  key    = "templates/index.html"
  source = "../templates/index.html"
  etag   = filemd5("../templates/index.html")
}

resource "aws_s3_object" "requirements" {
  bucket = aws_s3_bucket.app_code.id
  key    = "requirements.txt"
  source = "../requirements.txt"
  etag   = filemd5("../requirements.txt")
}

resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/upwind/phishing-app"
  retention_in_days = 7
}

resource "aws_iam_role" "ec2_role" {
  name = "upwind-ec2-cloudwatch-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cw_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "s3_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "upwind-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

locals {
  cw_config = jsonencode({
    logs = {
      logs_collected = {
        files = {
          collect_list = [
            {
              file_path       = "/var/log/phishing-app.log"
              log_group_name  = "/upwind/phishing-app"
              log_stream_name = "{instance_id}"
            }
          ]
        }
      }
    }
  })

  user_data_script = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y python3-pip amazon-cloudwatch-agent

    mkdir -p /opt/app/templates
    aws s3 cp s3://${aws_s3_bucket.app_code.bucket}/ /opt/app/ --recursive
    pip3 install -r /opt/app/requirements.txt

    echo '${local.cw_config}' > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

    export DB_HOST="${aws_db_instance.postgres.address}"
    export DB_NAME="phishingdb"
    export DB_USER="postgres"
    export DB_PASSWORD="${var.db_password}"

    cd /opt/app
    nohup python3 -u app.py > /var/log/phishing-app.log 2>&1 &
  EOF
}

resource "aws_instance" "app_1" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_a.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  user_data              = local.user_data_script
  depends_on             = [aws_s3_object.app_py, aws_s3_object.director_py, aws_s3_object.index_html, aws_s3_object.requirements]
  tags                   = { Name = "upwind-app-1" }
}

resource "aws_instance" "app_2" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_b.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  user_data              = local.user_data_script
  depends_on             = [aws_s3_object.app_py, aws_s3_object.director_py, aws_s3_object.index_html, aws_s3_object.requirements]
  tags                   = { Name = "upwind-app-2" }
}

resource "aws_lb" "alb" {
  name               = "upwind-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.subnet_a.id, aws_subnet.subnet_b.id]
}

resource "aws_lb_target_group" "tg" {
  name     = "upwind-tg"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  health_check {
    path                = "/health"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_target_group_attachment" "att_1" {
  target_group_arn = aws_lb_target_group.tg.arn
  target_id        = aws_instance.app_1.id
  port             = 5000
}

resource "aws_lb_target_group_attachment" "att_2" {
  target_group_arn = aws_lb_target_group.tg.arn
  target_id        = aws_instance.app_2.id
  port             = 5000
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}

output "alb_url" {
  value = "http://${aws_lb.alb.dns_name}"
}