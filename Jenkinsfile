pipeline {
    agent any

    environment {
        PYTHON_INSTALLER = 'https://www.python.org/ftp/python/3.13.0/python-3.13.0-arm64.exe'
        PYTHON_DIR = 'C:\\Python313'

        SMTP_HOST        = credentials('smtp-host')
        SMTP_PORT        = '587'
        SMTP_USER        = credentials('smtp-user')
        SMTP_PASS        = credentials('smtp-pass')
        REPORT_FROM      = credentials('sender-email')
        REPORT_TO        = credentials('receiver-email')
        
        CONFLUENCE_BASE  = credentials('confluence-base')
        CONFLUENCE_USER  = credentials('confluence-user')
        CONFLUENCE_TOKEN = credentials('confluence-token')
        CONFLUENCE_SPACE = 'DEMO'
        CONFLUENCE_TITLE = 'Test Result Report'
        GITHUB_CREDENTIALS = credentials('github-credentials')

        REPORT_PATH   = 'report/report.html'
        REPORT_DIR    = 'report'
        REPORT_ENH    = 'report/test_result_report_enhanced.html'
        VENV_PATH     = '.venv'
        VERSION_FILE  = 'report/version.txt'
    }

    stages {

        stage('Install Python if Missing') {
            steps {
                bat '''
                    @echo off
                    where python >nul 2>nul
                    if %ERRORLEVEL% neq 0 (
                        echo Installing Python...
                        powershell -Command "Invoke-WebRequest -Uri %PYTHON_INSTALLER% -OutFile python-installer.exe"
                        start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_test=0 TargetDir=%PYTHON_DIR%
                        del python-installer.exe
                    )
                    python --version
                    pip --version
                '''
            }
        }

        stage('Setup Python Environment') {
            steps {
                bat '''
                    if not exist "%VENV_PATH%" python -m venv %VENV_PATH%
                    %VENV_PATH%\\Scripts\\python.exe --version
                    %VENV_PATH%\\Scripts\\pip.exe --version
                '''
            }
        }

        stage('Checkout from GitHub') {
            steps {
                echo 'Checking out source code...'
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
                    %VENV_PATH%\\Scripts\\python.exe -m pip install beautifulsoup4 matplotlib
                """
            }
        }

        stage('Run Tests') {
            steps {
                bat """
                    if not exist "%REPORT_DIR%" mkdir %REPORT_DIR%
                    set PYTHONPATH=%CD%
                    echo Running tests...
                    %VENV_PATH%\\Scripts\\python.exe -m pytest --html=%REPORT_PATH% --self-contained-html || exit /b 0
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'report/report.html', fingerprint: true
                }
            }
        }

        stage('Enhance Report (Graphical Summary)') {
            steps {
                bat """
                    echo Enhancing report with charts...
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe enhance_report.py
                """
            }
            post {
                always {
                    echo "📦 Archiving enhanced HTML reports..."
                    archiveArtifacts artifacts: 'report/test_result_report_*_enhanced.html', fingerprint: true
                }
            }
        }

        stage('Test Confluence API') {
            steps {
                bat """
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe check_api_token.py
                """
            }
        }

        stage('Email Report') {
            steps {
                bat """
                    echo Sending enhanced report via email...
                    set PYTHONUTF8=1
                    set REPORT_PATH=%REPORT_ENH%
                    %VENV_PATH%\\Scripts\\python.exe send_report_email.py
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: "${VERSION_FILE}", onlyIfSuccessful: true
                }
            }
        }

        stage('Publish to Confluence') {
            steps {
                script {
                    echo "📥 Restoring version.txt..."
                    try {
                        unarchive mapping: ["${VERSION_FILE}" : "${VERSION_FILE}"]
                    } catch (err) {
                        echo "⚠️ No version.txt found — starting from v1."
                    }
                }
                bat """
                    echo Publishing enhanced HTML report to Confluence...
                    set PYTHONUTF8=1
                    set REPORT_PATH=%REPORT_ENH%
                    %VENV_PATH%\\Scripts\\python.exe publish_to_confluence.py
                """
            }
        }
    }

    post {
        success { echo '✅ Pipeline completed successfully!' }
        failure { echo '❌ Pipeline failed. Check logs!' }
    }
}
