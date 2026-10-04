from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import GithubActions
from diagrams.aws.security import IAM
from diagrams.aws.compute import ECR, EC2
from diagrams.aws.management import SystemsManager
from diagrams.programming.language import Python
from diagrams.aws.integration import SNS
from diagrams.aws.general import User

with Diagram("CERMS Dual CI-CD Pipeline Workflow", show=False, direction="LR"):
    
    dev = Github("Developer\n(Push Code / Tag)")
    pm = User("Project / Deploy\nManager")
    
    with Cluster("GitHub Actions CI/CD Plane"):
        gha_stg = GithubActions("Staging Runner\n(staging.yml)")
        gha_prod = GithubActions("Prod Runner\n(deploy.yml)")
        qa_parser = Python("Parse JSON Report\n& Annotations")
        
    with Cluster("Centralized AWS Services"):
        oidc = IAM("IAM OIDC\n(STS Token)")
        ecr = ECR("Amazon ECR\n(Docker Images)")
        ssm = SystemsManager("Systems Manager\n(Bastionless Deploy)")
        alert = SNS("Email Notification")
        
    with Cluster("Staging Environment"):
        ec2_stg = EC2("Staging Node")
        smoke_test_stg = Python("scan_urls.py\n(Smoke Test)")
        ec2_stg - smoke_test_stg
        
    with Cluster("Production Environment"):
        ec2_prod = EC2("Production Node")
        smoke_test_prod = Python("scan_urls.py\n(Smoke Test)")
        ec2_prod - smoke_test_prod
        
    # Staging Workflow (Blue)
    dev >> Edge(color="blue", label="1. Push 'main'") >> gha_stg
    gha_stg >> Edge(color="blue", label="2. OIDC Auth") >> oidc
    gha_stg >> Edge(color="blue", label="3. Build & Push :staging") >> ecr
    gha_stg >> Edge(color="blue", label="4. ssm send-command") >> ssm
    ssm >> Edge(color="blue", label="5. Pull, Migrate & Run (Staging)") >> ec2_stg
    smoke_test_stg >> Edge(color="blue", label="6. Output JSON") >> qa_parser
    
    # Production Workflow (Green)
    dev >> Edge(color="darkgreen", label="1. Push Tag 'v*'") >> gha_prod
    gha_prod >> Edge(color="darkgreen", label="2. OIDC Auth") >> oidc
    gha_prod >> Edge(color="darkgreen", label="3. Re-tag :staging to v* (Zero Rebuild)") >> ecr
    gha_prod >> Edge(color="darkgreen", label="4. ssm send-command") >> ssm
    ssm >> Edge(color="darkgreen", label="5. Pull, Migrate & Run (Prod)") >> ec2_prod
    smoke_test_prod >> Edge(color="darkgreen", label="6. Output JSON") >> qa_parser
    
    # Alerting Workflow (Red)
    qa_parser >> Edge(color="red", label="7. Status Report") >> alert
    alert >> Edge(color="red", label="8. Deployment Alert Email") >> pm