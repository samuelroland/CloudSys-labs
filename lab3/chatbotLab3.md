# Chatbot lab

## Set up environment:
To access Switch Engine, add the `clouds.yaml` file to the switch folder.
Also add the `switchengine-tsm-cloudsys.pem` key pair to the switch folder.
These files will be used in the `create_instance_switch.py` script.

TODO: create a requirement.txt file to install python lib?

## Object storage Creation
TODO

## Vector Store Creation
TODO

## Step 3: Vectorizing the PDF Files: 
TODO

## Create switch Instance

```sh
$ pip install openstacksdk
$ python create_instance_switch.py 
Create Server:
ssh -i ./switchengine-tsm-cloudsys.pem ubuntu@2001:620:5ca1:2f0:f816:3eff:feae:87f8
List Servers:
groupd-labo1 - ACTIVE - 78f67707-26ab-4b57-8d6c-81c004df1853
```

If needed, you can use the `delete_server` function in the same script.

## Accessing the application
TODO
