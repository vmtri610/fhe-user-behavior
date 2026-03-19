pipeline {
    agent any

    options{
        // Max number of build logs to keep and days to keep
        buildDiscarder(logRotator(numToKeepStr: '5', daysToKeepStr: '5'))
        // Enable timestamp at each job in the pipeline
        timestamps()
    }

    environment{
        registry = 'asia-southeast1-docker.pkg.dev/robusto-ai-dev-490114/fhe-repo/fastapi-server'
        client_registry = 'asia-southeast1-docker.pkg.dev/robusto-ai-dev-490114/fhe-repo/gradio-client'
    }

    stages {
        stage('Test') {
            steps {
                script {
                    echo 'Running tests with Docker build...'
                    sh '''
                        docker build -t test-image -f Dockerfile .
                        docker run --rm test-image bash -c "
                            cd /app &&
                            PYTHONPATH=/app pytest backend/tests --cov=backend/app --cov-report=term --cov-report=xml -v
                        "
                        docker rmi test-image
                    '''
                }
            }
        }
        stage('Build & Push Images') {
            steps {
                script {
                    echo "Building images for build number ${BUILD_NUMBER}..."
                    
                    // Login to Google Artifact Registry
                    sh """#!/bin/bash
                        set +x
                        TOKEN=\$(curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
                        echo \$TOKEN | docker login -u oauth2accesstoken --password-stdin https://asia-southeast1-docker.pkg.dev >/dev/null 2>&1
                        set -x
                        
                        # Build & Push Server
                        docker build -t ${registry}:${BUILD_NUMBER} -f Dockerfile .
                        docker tag ${registry}:${BUILD_NUMBER} ${registry}:latest
                        docker push ${registry}:${BUILD_NUMBER}
                        docker push ${registry}:latest
                        
                        # Build & Push Client
                        docker build -t ${client_registry}:${BUILD_NUMBER} -f Dockerfile.client .
                        docker tag ${client_registry}:${BUILD_NUMBER} ${client_registry}:latest
                        docker push ${client_registry}:${BUILD_NUMBER}
                        docker push ${client_registry}:latest
                    """
                }
            }
        }
        stage('Update Helm (GitOps)') {
            steps {
                script {
                    echo "Updating Helm chart with new image tags: ${BUILD_NUMBER}"
                    // This assumes Jenkins has permissions to push to the repo
                    sh """
                        # Update the tags in values.yaml
                        sed -i "s/tag: .*/tag: \\"${BUILD_NUMBER}\\"/g" helm/fhe-user-behavior/values.yaml
                        
                        # Commit and push back to Git
                        git config user.email "jenkins@robusto-ai.com"
                        git config user.name "Jenkins CI"
                        git add helm/fhe-user-behavior/values.yaml
                        git commit -m "chore: update image tags to ${BUILD_NUMBER} [skip ci]"
                        git push origin main
                    """
                }
            }
        }
    }
}