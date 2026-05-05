provider "aws" {
  region = "us-east-1"
}

resource "aws_security_group" "flask_sg" {
  name = "flask-sg"

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_instance" "flask_server" {
  ami           = "ami-0c02fb55956c7d316" # Amazon Linux 2 (us-east-1)
  instance_type = "t2.micro"

  security_groups = [aws_security_group.flask_sg.name]

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install python3 git -y
    EOF
from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Flask running on EC2"

app.run(host="0.0.0.0", port=5000)
EOT

              python3 app.py &
              EOF

  tags = {
    Name = "flask-ec2"
  }
}
