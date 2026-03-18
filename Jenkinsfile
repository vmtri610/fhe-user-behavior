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
        stage('Build') {
            steps {
                script {
                    echo 'Building image for deployment..'
                    dockerImage = docker.build registry + ":$BUILD_NUMBER" 
                    echo 'Pushing image to dockerhub..'
                    sh """#!/bin/bash
                        set +x
                        TOKEN=\$(curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
                        echo \$TOKEN | docker login -u oauth2accesstoken --password-stdin https://asia-southeast1-docker.pkg.dev >/dev/null 2>&1
                        set -x
                        docker push ${registry}:${BUILD_NUMBER}
                        docker tag ${registry}:${BUILD_NUMBER} ${registry}:latest
                        docker push ${registry}:latest
                    """
                }
            }
        }
    }
}