#!/bin/bash

# =============================================
# Kubernetes Cluster Setup and Deployment Script
# =============================================

# Delete any existing cluster
echo "🗑️  Deleting any existing kind cluster..."
read -p ""
kind delete cluster
echo "✅ Existing cluster deleted. Press Enter to continue..."
read -p ""

echo "🚀 Starting Kubernetes cluster creation using kind -> kind create cluster --config kind-config.yaml"
read -p ""
kind create cluster --config kind-config.yaml
echo "✅ Cluster created successfully. Press Enter to continue..."
read -p ""

# Get all resources using kubectl
echo "📋 Listing all Kubernetes resources in the cluster -> kubectl get all"
read -p ""
kubectl get all
echo "✅ Resources listed. Press Enter to continue..."
read -p ""

# Show the nodes in Docker
echo "🐳 Displaying Docker containers (Kubernetes nodes) -> docker ps"
read -p ""
docker ps
echo "✅ Docker nodes listed. Press Enter to continue..."
read -p ""

echo "📝 Viewing Data Retrieval Deployment File"
read -p ""
cat redis-deployment.yaml
echo "✅ Data Retrieval Deployment File displayed. Press Enter to continue..."
read -p ""

echo "🔴 Deploying Redis Application -> kubectl apply -f redis-deployment.yaml"
read -p ""
kubectl apply -f redis-deployment.yaml
echo "✅ Redis Application deployed successfully. Press Enter to continue..."
read -p ""

# Get the Redis pod name
echo "📋 Checking Redis deployment status -> kubectl get all"
read -p ""
kubectl get all
echo "✅ Redis pod status listed. Press Enter to continue..."
read -p ""

# Create a secret for the AWS access key and secret access key
echo "🔑 Creating AWS credentials secret -> kubectl create secret generic aws-secret --from-literal=AWS_ACCESS_KEY_ID=<YOUR ACCESS KEY> --from-literal=AWS_SECRET_ACCESS_KEY=<YOUR SECRET ACCESS KEY>"
read -p ""
kubectl create secret generic aws-secret --from-literal=AWS_ACCESS_KEY_ID=... --from-literal=AWS_SECRET_ACCESS_KEY=...
echo "✅ AWS secret created successfully. Press Enter to continue..."
read -p ""

# View the secret
echo "🔍 Viewing AWS secret details -> kubectl get secret aws-secret"
read -p ""
kubectl get secret aws-secret
echo "✅ AWS secret details displayed. Press Enter to continue..."
read -p ""

# Data Retrieval Container Build
echo "🏗️ Building Data Retrieval Container -> docker build -t nabilabdennadher/data-retrieval-supcom2025:latest data-retrieval/."
read -p ""
docker build -t nabilabdennadher/data-retrieval-supcom2025:latest data-retrieval/.
echo "✅ Data Retrieval Container built successfully. Press Enter to continue..."
read -p ""

# Push the Data Retrieval Container to Docker Hub
echo "📤 Pushing Data Retrieval Container to Docker Hub -> docker push nabilabdennadher/data-retrieval-supcom2025:latest"
read -p ""
docker push nabilabdennadher/data-retrieval-supcom2025:latest
echo "✅ Data Retrieval Container pushed to Docker Hub. Press Enter to continue..."
read -p ""

echo "📝 Viewing Data Retrieval Deployment File"
read -p ""
cat data-retrieval-deployment.yaml
echo "✅ Data Retrieval Deployment File displayed. Press Enter to continue..."
read -p ""

echo "🚀 Deploying Data Retrieval Container to Kubernetes -> kubectl apply -f data-retrieval-deployment.yaml"
read -p ""
kubectl apply -f data-retrieval-deployment.yaml
echo "✅ Data Retrieval Container deployed successfully. Press Enter to continue..."
read -p ""

echo "📋 Checking Data Retrieval Container deployment status -> kubectl get all"
read -p ""
kubectl get all
echo "✅ Data Retrieval Container status listed. Press Enter to continue..."
read -p ""

echo "📝 Viewing Data Retrieval Container logs -> kubectl logs -f \$(kubectl get pods -l app=data-retrieval-pod -o jsonpath='{.items[0].metadata.name}')"
read -p ""
pod_name=$(kubectl get pods -l app=data-retrieval-pod -o jsonpath='{.items[0].metadata.name}')
kubectl logs -f $pod_name
echo "✅ Data Retrieval Container logs displayed. Press Enter to continue..."
read -p ""

# Create the Forecast Application
echo "🏗️ Building Forecast Application container -> docker build -t nabilabdennadher/forecast-supcom2025:latest forecast/."
read -p ""
docker build -t nabilabdennadher/forecast-supcom2025:latest forecast/.
echo "✅ Forecast Application container built successfully. Press Enter to continue..."
read -p ""

# Push the Forecast Application container to Docker Hub
echo "📤 Pushing Forecast Application container to Docker Hub -> docker push nabilabdennadher/forecast-supcom2025:latest"
read -p ""
docker push nabilabdennadher/forecast-supcom2025:latest
echo "✅ Forecast Application container pushed to Docker Hub. Press Enter to continue..."
read -p ""

# Deploy the Forecast Application
echo "🚀 Deploying Forecast Application to Kubernetes -> kubectl apply -f forecast-deployment.yaml"
read -p ""
kubectl apply -f forecast-deployment.yaml
echo "✅ Forecast Application deployed successfully. Press Enter to continue..."
read -p ""

# Wait for Forecast pod to be ready
echo "⏳ Waiting for Forecast pod to be ready..."
kubectl wait --for=condition=ready pod -l app=forecast-pod --timeout=450s
echo "✅ Forecast pod is ready. Press Enter to continue..."
read -p ""

# Get the Forecast Application pod name
echo "📋 Checking Forecast Application deployment status -> kubectl get all"
read -p ""
kubectl get all
echo "✅ Forecast Application status listed. Press Enter to continue..."
read -p ""

# check the logs of the Forecast Application
echo "📝 Viewing Forecast Container logs -> kubectl logs -f \$(kubectl get pods -l app=forecast-pod -o jsonpath='{.items[0].metadata.name}')"
read -p ""
pod_name=$(kubectl get pods -l app=forecast-pod -o jsonpath='{.items[0].metadata.name}')
kubectl logs $pod_name
echo "✅ Forecast Application logs displayed. Press Enter to continue..."
read -p ""

# Deploy the Grafana Application
echo "📊 Deploying Grafana Application -> kubectl apply -f grafana-deployment.yaml"
read -p ""
kubectl apply -f grafana-deployment.yaml
echo "✅ Grafana Application deployed successfully. Press Enter to continue..."
read -p ""

# Wait for Grafana pod to be ready
echo "⏳ Waiting for Grafana pod to be ready..."
kubectl wait --for=condition=ready pod -l app=grafana-pod --timeout=120s
echo "✅ Grafana pod is ready. Press Enter to continue..."
read -p ""

# Get the Grafana Application pod name
echo "📋 Checking Grafana Application deployment status -> kubectl get all"
read -p ""
kubectl get all
echo "✅ Grafana Application status listed. Press Enter to continue..."
read -p ""

# Port forward the Grafana Application
echo "🔌 Setting up port forwarding for Grafana -> kubectl port-forward \$(kubectl get pods -l app=grafana-pod -o jsonpath='{.items[0].metadata.name}') 3000:3000"
read -p ""
pod_name=$(kubectl get pods -l app=grafana-pod -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward $pod_name 3000:3000
echo "✅ Grafana port forwarding established. Press Enter to continue..."
read -p ""














