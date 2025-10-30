pipeline {
    agent any
    options { timestamps() }

    environment {
        // ===== Core Credentials =====
        SMTP_HOST = credentials('smtp-host')
        SMTP_PORT = '587'
        SMTP_USER = credentials('smtp-user')
        SMTP_PASS = credentials('smtp-pass')
        REPORT_FROM = credentials('sender-email')
        REPORT_TO = credentials('receiver-email')

        CONFLUENCE_BASE  = credentials('confluence-base')
        CONFLUENCE_USER  = credentials('confluence-user')
        CONFLUENCE_TOKEN = credentials('confluence-token')
        CONFLUENCE_SPACE = 'DEMO'
        CONFLUENCE_TITLE = 'Test Result Report'

        GITHUB_CREDENTIALS = credentials('github-credentials')

        // ===== Paths & Config =====
        VENV_PATH = '.venv'
        REPORT_DIR = 'report'
        VERSION_FILE = 'report/version.txt'
        REPORT_BASENAME = 'test_result_report'
        PYTHONUTF8 = '1'
        PYTHONIOENCODING = 'utf-8'
        PYTHONLEGACYWINDOWSSTDIO = '1'
    }

    stages {
        stage('Setup Environment') {
            steps {
                echo '🛠 Setting up Python virtual environment...'
                bat '''
                    @echo off
                    chcp 65001 >nul
                    if not exist "%VENV_PATH%" python -m venv %VENV_PATH%
                    %VENV_PATH%\\Scripts\\pip install --upgrade pip
                    %VENV_PATH%\\Scripts\\pip install -r requirements.txt pytest matplotlib reportlab requests beautifulsoup4
                '''
            }
        }

        stage('Run Tests & Generate PDF Report') {
            steps {
                echo '🧪 Running tests and generating PDF report...'
                bat '''
                    @echo off
                    if not exist report mkdir report
                    set PYTHONPATH=%CD%
                    %VENV_PATH%\\Scripts\\python -m pytest --maxfail=1 --disable-warnings -q > report\\pytest_output.txt
                    %VENV_PATH%\\Scripts\\python enhance_report.py
                '''
            }
        }

        stage('Verify Confluence Access') {
            steps {
                echo '🔑 Verifying Confluence API token...'
                bat "%VENV_PATH%\\Scripts\\python check_api_token.py"
            }
        }

        stage('Send Email Report') {
            steps {
                echo '📧 Sending latest PDF report via email...'
                bat "%VENV_PATH%\\Scripts\\python send_report_email.py"
            }
        }

        stage('Publish to Confluence') {
            steps {
                echo '🌐 Uploading PDF report to Confluence...'
                bat "%VENV_PATH%\\Scripts\\python publish_to_confluence.py"
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline completed successfully.'
        }
        failure {
            echo '❌ Pipeline failed — version not incremented.'
        }
        always {
            echo '🧹 Cleanup complete.'
        }
    }
}
