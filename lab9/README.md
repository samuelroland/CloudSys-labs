# Lab: Cloud Provisioning
**Authors**: Olivia Manz and Samuel Roland in **Group D**

See [the instructions](https://github.com/SoftEng-HEIGVD/Teaching-MSE-TSM-CloudSys-2022-Labs/tree/main/Lab%20Cloud%20Provisioning) if necessary.

### Lab convention for naming cloud resources
We will use the following __lab naming convention:__ the name of every cloud resource starts with the group, followed by our last name and finnaly the type of object

    GrD-RolandManz-xxx
    
# Part 1 - CloudFormation
## Task 1.2: Launch a stack
To create the stack, we will choose a existing subnet with Auto-assign public IPv4 address=yes. For the VPC, we choose the VPC with the previous subnet assigned.
In our case, we choose:
- subnet id: subnet-032ade9da5a97829a
- vpc: vpc-037435ee28ff909f8 


> What tags did CloudFormation add to the EC2 Instance? Which tag is used by CloudFormation to uniquely identify the resource?

Tags of EC2 instance

| **Key**                              | **Value**                                                                                                  |
|-------------------------------------|-------------------------------------------------------------------------------------------------------------|
| aws:cloudformation:stack-name       | GrD-RolandManz-master                                                                                       |
| aws:cloudformation:stack-id         | arn:aws:cloudformation:us-east-1:067128346383:stack/GrD-RolandManz-master/b4c61160-bf25-11f0-a8ce-129715c41913 |
| Name                                | LAMP-WebServer                                                                                              |
| CloudFormationTest                  | true                                                                                                        |
| aws:cloudformation:logical-id       | WebServer                                                                                                   |

`aws:cloudformation:stack-id` is used by CloudFormation to uniquely identify the resource

> How did CloudFormation name the Security Group and what tags did it add?

The Security Group name is `sg-040d15266e4fbd60b (GrD-RolandManz-master-WebServerSecurityGroup-kIRPaFqz3wei)`

Security group tags:

| **Key**                            | **Value**                                                                                                  |
|-----------------------------------|-------------------------------------------------------------------------------------------------------------|
| aws:cloudformation:stack-id       | arn:aws:cloudformation:us-east-1:067128346383:stack/GrD-RolandManz-master/b4c61160-bf25-11f0-a8ce-129715c41913 |
| aws:cloudformation:stack-name     | GrD-RolandManz-master                                                                                       |
| CloudFormationTest                | true                                                                                                        |
| aws:cloudformation:logical-id     | WebServerSecurityGroup                                                                                      |


> The template specified an output parameter _WebsiteURL_. What is its value?  

In our case the value is `44.211.131.166`. It's the public IPv4 address of EC2 instance created.

> The LAMP Stack template by AWS makes things appear easier than they are. They use an ugly hack to make the selection of the instance type easy for the user of the template, but it makes the template difficult to maintain. Explain the hack.

To make it easier to select the instance type and create a dropdown list, the template hardcodes the possible instance types:
```yaml
  InstanceType:
    Type: String
    Default: t2.micro
    AllowedValues:
      - t2.micro
      - t2.small
      - t2.medium
      - t3.micro
      - t3.small
      - t3.medium
```
It’s the same for the `osVersion` and `ImageId` parameters.
However, if AWS adds new instance types, the template must be updated manually, it’s not dynamic. Moreover, some instance types are not available in all regions.
Here, the possible choices are hardcoded to avoid incompatible configurations.

# Part 2 - Terraform

```console
> terraform init
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)
Terraform has created a lock file .terraform.lock.hcl to record the provider
selections it made above. Include this file in your version control repository
so that Terraform can guarantee to make the same selections by default when
you run "terraform init" in the future.

Terraform has been successfully initialized!

You may now begin working with Terraform. Try running "terraform plan" to see
any changes that are required for your infrastructure. All Terraform commands
should now work.

If you ever set or change modules or backend configuration for Terraform,
rerun this command to reinitialize your working directory. If you forget, other
commands will detect it and remind you to do so if necessary.
```

> What files were created in the terraform directory? Make sure to look also at hidden files and directories (ls -a). What are they used for?

```console
> tree -a
.
├── main.tf
├── .terraform
│   └── providers
│       └── registry.terraform.io
│           └── hashicorp
│               └── aws
│                   └── 5.100.0
│                       └── linux_amd64
│                           ├── LICENSE.txt
│                           └── terraform-provider-aws_v5.100.0_x5
└── .terraform.lock.hcl

```

Given this required plugin for AWS mentionned in `main.tf`, terraform needs to pick a version that respects the version constraints `"~> 5.0"` and download this plugin. In [the Operators section in Version constraints docs for the configuration language HCL](https://developer.hashicorp.com/terraform/language/expressions/version-constraints), we find that *`~>` Allows only the right-most version component to increment.* This means that we can have any `5.x` version matching this pattern.

```hcl
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
```

First, let's take about the `.terraform.lock.hcl` which is another lock file (like `package-lock.json`) used to pin the versions of required plugins.

```hcl
provider "registry.terraform.io/hashicorp/aws" {
  version     = "5.100.0"
  constraints = "~> 5.0"
  hashes = [
    "h1:edXOJWE4ORX8Fm+dpVpICzMZJat4AX0VRCAy/xkcOc0=",
    "zh:054b8dd49f0549c9a7cc27d159e45327b7b65cf404da5e5a20da154b90b8a644",
...
```
As we can see it has taken the `5.100.0` version for the `hashicorp/aws` plugin, on the default registry. According to the section [New provider package checksums](https://developer.hashicorp.com/terraform/language/files/dependency-lock#new-provider-package-checksums), the `hashes` key contain hashes of the plugin to verify its integrity.
