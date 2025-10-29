pipeline {
    agent any

    environment {
        // Python Installer and Directory
        PYTHON_INSTALLER = 'https://www.python.org/ftp/python/3.13.0/python-3.13.0-arm64.exe'
        PYTHON_DIR = 'C:\\Python313'

        // Credentials
        SMTP_HOST        = credentials('smtp-host')
        SMTP_PORT        = '587'
        SMTP_USER        = credentials('smtp-user')
        SMTP_PASS        = credentials('smtp-pass')

        // Email sender and Receiver
        REPORT_FROM      = credentials('sender-email')
        REPORT_TO        = credentials('receiver-email')
        
        // Confluence login configuration
        CONFLUENCE_BASE  = credentials('confluence-base')
        CONFLUENCE_USER  = credentials('confluence-user')
        CONFLUENCE_TOKEN = credentials('confluence-token')
        
        // Confluence Space and report configuration
        CONFLUENCE_SPACE = 'DEMO'
        CONFLUENCE_TITLE = 'Test Result Report'

        // GitHub login credentials Configuration
        GITHUB_CREDENTIALS = credentials('github-credentials')

        // Paths
        REPORT_PATH = 'report/report.html'
        VENV_PATH   = '.venv'
    }

    stages {
        stage('Install Python if Missing') {
            steps {
                bat '''
                    @echo off
                    echo Checking if Python is installed...
                    where python >nul 2>nul
                    if %ERRORLEVEL% neq 0 (
                        echo Python not found. Downloading installer...
                        powershell -Command "Invoke-WebRequest -Uri %PYTHON_INSTALLER% -OutFile python-installer.exe"

                        echo Installing Python silently...
                        start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_test=0 TargetDir=%PYTHON_DIR%

                        echo Cleaning up installer...
                        del python-installer.exe
                    ) else (
                        echo Python already installed.
                    )

                    echo Verifying installation...
                    python --version
                    pip --version
                '''
            }
        }

        stage('Setup Python Environment') {
            steps {
                bat '''
                    @echo off
                    echo Creating virtual environment if it doesn't exist...
                    if not exist "%VENV_PATH%" (
                        python -m venv %VENV_PATH%
                    )

                    echo Python & pip in venv:
                    %VENV_PATH%\\Scripts\\python.exe --version
                    %VENV_PATH%\\Scripts\\pip.exe --version
                '''
            }
        }

        stage('Checkout from GitHub') {
            steps {
                echo 'Checking out source code from GitHub repository...'
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[
                        url: 'https://github.com/devopsuser8413/flask-login-ci-confluence-win-test.git',
                        credentialsId: 'github-credentials'
                    ]]
                ])
            }
        }

        stage('Install Dependencies') {
            steps {
                bat """
                    echo Installing dependencies...
                    %VENV_PATH%\\Scripts\\python.exe -m pip install --upgrade pip
                    %VENV_PATH%\\Scripts\\python.exe -m pip install -r requirements.txt
                """
            }
        }

        stage('Run Tests') {
            steps {
                bat """
                    echo Running tests...
                    if not exist "report" mkdir report
                    set PYTHONPATH=%CD%
                    %VENV_PATH%\\Scripts\\python.exe -m pytest --html=%REPORT_PATH% --self-contained-html || exit /b 0
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'report\\report.html', fingerprint: true
                }
            }
        }

        stage('Test Confluence API') {
            steps {
                bat """
                    echo Verifying Confluence API...
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe check_api_token.py
                """
            }
        }

        stage('Publish to Confluence') {
            steps {
                bat """
                    echo Publishing HTML report to Confluence...
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe publish_to_confluence.py
                """
            }
        }

        stage('Email Report') {
            steps {
                bat """
                    echo Sending test report via email...
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe send_report_email.py
                """
            }
        }

    }

    post {
        success { echo '✅ Pipeline completed successfully!' }
        failure { echo '❌ Pipeline failed. Check logs!' }
    }
}
