from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import CloudFront, Route53, VPC, PublicSubnet, InternetGateway, NATGateway
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.storage import S3
from diagrams.aws.management import SystemsManager, Cloudwatch
from diagrams.aws.integration import SNS
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import GithubActions
from diagrams.aws.security import IAM
from diagrams.aws.compute import ECR
from diagrams.onprem.network import Nginx
from diagrams.programming.framework import Django
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.database import Mariadb
from diagrams.onprem.queue import Celery

with Diagram("CERMS Enterprise Cloud & DevOps Architecture", show=False, direction="TB"):

    with Cluster("Global Edge & Ingress Layer"):
        cf = CloudFront("CloudFront CDN\n(TLS 1.2/1.3)")
        igw = InternetGateway("Internet Gateway\n(0.0.0.0/0)")

        cf >> Edge(label="/static, /media (Cache)") >> cf
        cf >> Edge(label="Dynamic Traffic") >> igw

    with Cluster("AWS VPC (10.0.0.0/16)"):
        with Cluster("Production Subnet (ap-south-1a)"):
            ec2_prod = EC2("EC2 Prod Node\n(Graviton2 t3.micro)")
            
            with Cluster("Docker Bridge (172.28.0.0/16)"):
                nginx = Nginx("Nginx Proxy\n(:80/443)")
                web = Django("Django Web\n(Gunicorn :8000)")
                celery = Celery("Celery Worker")
                db = Mariadb("MariaDB 10.11")
                redis = Redis("Redis 7.2")

                nginx >> Edge(label="proxy_pass :8000") >> web
                web >> db
                web >> redis
                celery >> db
                celery >> redis
            
            ec2_prod - nginx

        with Cluster("Staging Subnet (ap-south-1b)"):
            ec2_stage = EC2("EC2 Staging Node")

        igw >> ec2_prod
        igw >> ec2_stage

    with Cluster("Centralized Governance & Storage"):
        ecr = ECR("Amazon ECR")
        s3 = S3("Central S3 DR\n(AES-256)")
        glacier = S3("S3 Glacier\n(30-Day Transition)")
        cw = Cloudwatch("CloudWatch")
        sns = SNS("SNS Alerts")

        s3 >> Edge(label="Lifecycle Rule") >> glacier
        ec2_prod >> Edge(label="Nightly Encrypted Backup", style="dashed") >> s3
        ec2_prod >> Edge(label="Metrics & Health", style="dashed") >> cw
        cw >> sns

    with Cluster("CI/CD Pipeline (GitHub Actions)"):
        gh = Github("Developer / Git")
        gha = GithubActions("GitHub Actions Runner")
        oidc = IAM("AWS IAM OIDC (STS)")

        gh >> Edge(label="Push to main (Staging) / Tag (Prod)") >> gha
        gha >> Edge(label="Auth Request") >> oidc
        oidc >> Edge(label="Temp Credentials") >> gha
        
        gha >> Edge(label="Build/Retag Image") >> ecr
        
        ssm = SystemsManager("AWS SSM")
        gha >> Edge(label="aws ssm send-command") >> ssm
        
        ssm >> Edge(label="Deploy & Test") >> ec2_stage
        ssm >> Edge(label="Deploy & Test") >> ec2_prod