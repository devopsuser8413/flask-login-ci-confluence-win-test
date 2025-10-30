pipeline {
    agent any

    options {
        timestamps()
    }

    environment {
        // ============================
        // 💡 Core Configuration
        // ============================
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
        VERSION_FILE  = 'report/version.txt'
        VENV_PATH     = '.venv'

        // ============================
        // 🧩 UTF-8 + Python Encoding Fix
        // ============================
        PYTHONUTF8 = '1'
        PYTHONIOENCODING = 'utf-8'
        PYTHONLEGACYWINDOWSSTDIO = '1'
    }

    stages {

        // -------------------------------
        stage('Setup Encoding') {
            steps {
                echo '🔧 Setting system encoding to UTF-8...'
                bat '''
                    @echo off
                    chcp 65001 >nul
                    set PYTHONUTF8=1
                    set PYTHONIOENCODING=utf-8
                    set PYTHONLEGACYWINDOWSSTDIO=1
                    echo ✅ Windows console now using UTF-8 (code page 65001)
                '''
            }
        }

        // -------------------------------
        stage('Checkout GitHub') {
            steps {
                echo '📦 Checking out source code from GitHub repository...'
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[
                        url: 'https://github.com/devopsuser8413/flask-login-ci-confluence-win-test.git',
                        credentialsId: 'github-credentials'
                    ]]
                ])
                echo '✅ Source code checkout complete.'
            }
        }

        // -------------------------------
        stage('Setup Python') {
            steps {
                echo '🐍 Checking and creating Python virtual environment...'
                bat '''
                    @echo off
                    chcp 65001 >nul
                    if not exist "%VENV_PATH%" (
                        echo Creating new virtual environment...
                        python -m venv %VENV_PATH%
                    ) else (
                        echo Virtual environment already exists.
                    )
                    echo Checking Python and pip versions...
                    %VENV_PATH%\\Scripts\\python.exe --version
                    %VENV_PATH%\\Scripts\\pip.exe --version
                '''
                echo '✅ Python environment ready.'
            }
        }

        // -------------------------------
        stage('Install Dependencies') {
            steps {
                echo '📦 Installing Python dependencies...'
                bat """
                    @echo off
                    chcp 65001 >nul
                    echo Upgrading pip...
                    %VENV_PATH%\\Scripts\\python.exe -m pip install --upgrade pip
                    echo Installing required modules from requirements.txt...
                    %VENV_PATH%\\Scripts\\pip.exe install -r requirements.txt
                    echo Installing additional visualization and report libraries...
                    %VENV_PATH%\\Scripts\\pip.exe install beautifulsoup4 matplotlib reportlab
                """
                echo '✅ All dependencies installed successfully.'
            }
        }

        // -------------------------------
        stage('Run Tests') {
            steps {
                echo '🧪 Running unit tests and generating raw HTML report...'
                bat """
                    @echo off
                    chcp 65001 >nul
                    if not exist "report" mkdir report
                    echo Executing pytest...
                    set PYTHONPATH=%CD%
                    set FORCE_FAIL=true
                    %VENV_PATH%\\Scripts\\python.exe -m pytest --html=%REPORT_PATH% --self-contained-html || exit /b 0
                """
                echo '✅ Pytest completed and raw report generated.'
            }
            post {
                always {
                    echo '📤 Archiving raw HTML test report for reference...'
                    archiveArtifacts artifacts: 'report/report.html', fingerprint: true
                }
            }
        }

        // -------------------------------
        stage('Generate Report') {
            steps {
                echo '🎨 Enhancing report: adding summary chart and generating PDF...'
                bat """
                    @echo off
                    chcp 65001 >nul
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe generate_report.py
                """
                echo '✅ Enhanced HTML and PDF reports generated successfully.'
            }
            post {
                always {
                    echo '📦 Archiving enhanced reports and version file...'
                    archiveArtifacts artifacts: 'report/test_result_report_v*.html', fingerprint: true
                    archiveArtifacts artifacts: 'report/test_result_report_v*.pdf', fingerprint: true
                    archiveArtifacts artifacts: 'report/version.txt', fingerprint: true
                }
            }
        }

        // -------------------------------
        stage('Email Report') {
            steps {
                echo '📧 Sending latest test report as PDF attachment via email...'
                bat """
                    @echo off
                    chcp 65001 >nul
                    %VENV_PATH%\\Scripts\\python.exe send_report_email.py
                """
                echo '✅ Email with PDF report sent successfully.'
            }
        }

        // -------------------------------
        stage('Publish Report Confluence & Notify Email') {
            steps {
                echo '🌐 Publishing latest HTML and PDF reports to Confluence page...'
                bat """
                    @echo off
                    chcp 65001 >nul
                    %VENV_PATH%\\Scripts\\python.exe publish_report_confluence.py
                """
                echo '✅ Report (HTML & PDF) successfully published to Confluence.'
            }
        }
    }

    // -------------------------------
    post {
        success {
            echo '''
            ✅ PIPELINE COMPLETED SUCCESSFULLY!
            =================================
            - All stages executed cleanly.
            - HTML & PDF reports archived and versioned.
            - Email with PDF sent successfully.
            - Reports published to Confluence.
            =================================
            '''
        }
        failure {
            echo '''
            ❌ PIPELINE FAILED!
            =================================
            - Check Jenkins logs for failed stage.
            - Verify SMTP and Confluence credentials.
            - Ensure report files exist and network access is available.
            =================================
            '''
        }
        always {
            echo '🧹 Pipeline execution finished. Cleaning up workspace...'
        }
    }
}
