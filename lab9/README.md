# Lab: Cloud Provisioning
**Authors**: Olivia Manz and Samuel Roland in **Group D**

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
