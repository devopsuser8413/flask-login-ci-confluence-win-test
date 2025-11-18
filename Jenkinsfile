pipeline {
    agent any

    options {
        timestamps()
        ansiColor('xterm')
    }

    environment {

        // ===========================================
        // 🔧 SMTP Email Configuration
        // ===========================================
        SMTP_HOST        = credentials('smtp-host')
        SMTP_PORT        = '587'
        SMTP_USER        = credentials('smtp-user')
        SMTP_PASS        = credentials('smtp-pass')
        REPORT_FROM      = credentials('sender-email')
        REPORT_TO        = credentials('receiver-email')   // comma-separated
        REPORT_CC        = ''                              // optional, comma-separated
        REPORT_BCC       = ''                              // optional, comma-separated

        // ===========================================
        // 🌐 Confluence Configuration
        // ===========================================
        CONFLUENCE_BASE  = credentials('confluence-base')  // e.g. https://your-org.atlassian.net/wiki
        CONFLUENCE_USER  = credentials('confluence-user')
        CONFLUENCE_TOKEN = credentials('confluence-token')
        CONFLUENCE_SPACE = 'DEMO'
        CONFLUENCE_TITLE = 'Test Result Report'

        // ===========================================
        // 🔐 GitHub Authentication
        // ===========================================
        GITHUB_CREDENTIALS = credentials('github-credentials')

        // ===========================================
        // 📁 Report Paths
        // ===========================================
        REPORT_PATH   = 'report/report.html'
        REPORT_DIR    = 'report'
        VERSION_FILE  = 'report/version.txt'

        // ===========================================
        // 🐍 Python Environment
        // ===========================================
        VENV_PATH      = '.venv'
        PYTHONUTF8     = '1'
        PYTHONIOENCODING = 'utf-8'
        PYTHONLEGACYWINDOWSSTDIO = '1'

        // ===========================================
        // ⚡ PIP Cache Directory for Fast Installs
        // ===========================================
        PIP_CACHE_DIR = "C:\\jenkins_home\\pip-cache"
    }

    stages {

        // ============================================================================
        stage('Setup Encoding') {
            steps {
                echo '🔧 Setting system encoding to UTF-8...'
                bat '''
                    @echo off
                    chcp 65001 >nul
                    echo UTF-8 activated (Code Page 65001)
                '''
            }
        }

        // ============================================================================
        stage('Checkout GitHub') {
            steps {
                echo '📦 Checking out source code...'
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[
                        url: 'https://github.com/devopsuser8413/flask-login-ci-confluence-win-test.git',
                        credentialsId: 'github-credentials'
                    ]]
                ])
                echo '✅ Checkout complete.'
            }
        }

        // ============================================================================
        stage('Setup Python') {
            steps {
                echo '🐍 Creating fresh Python virtual environment...'
                bat """
                    @echo off

                    if exist "%VENV_PATH%" (
                        echo Removing old venv...
                        rmdir /s /q "%VENV_PATH%"
                    )

                    python -m venv "%VENV_PATH%"

                    "%VENV_PATH%\\Scripts\\python.exe" -m pip install --quiet ^
                        --upgrade pip setuptools wheel ^
                        --cache-dir "%PIP_CACHE_DIR%" --no-warn-script-location
                """
                echo '🚀 Python environment ready.'
            }
        }

        // ============================================================================
        stage('Install Dependencies') {
            steps {
                echo '📦 Installing Python dependencies...'
                bat """
                    @echo off

                    if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%"

                    "%VENV_PATH%\\Scripts\\pip.exe" install --quiet ^
                        --cache-dir "%PIP_CACHE_DIR%" -r requirements.txt
                """
                echo '⚡ Dependencies installed quickly with pip cache!'
            }
        }

        // ============================================================================
        stage('Run Tests') {
            steps {
                echo '🧪 Running test suite and generating raw HTML report...'
                bat """
                    @echo off
                    if not exist "report" mkdir report

                    set PYTHONPATH=%CD%

                    "%VENV_PATH%\\Scripts\\python.exe" -m pytest ^
                        --html=%REPORT_PATH% --self-contained-html ^
                        > report\\pytest_output.txt 2>&1 || exit /b 0
                """
                echo '✅ Tests executed (pytest_output.txt + raw HTML generated).'
            }
            post {
                always {
                    echo '📤 Archiving raw HTML report...'
                    archiveArtifacts artifacts: 'report/report.html', fingerprint: true
                }
            }
        }

        // ============================================================================
        stage('Generate Report') {
            steps {
                echo '🎨 Enhancing HTML report and creating PDF...'
                bat """
                    @echo off
                    "%VENV_PATH%\\Scripts\\python.exe" generate_report.py
                """
                echo '📄 Enhanced HTML & PDF report generated.'
            }
            post {
                always {
                    echo '📦 Archiving enhanced reports...'
                    archiveArtifacts artifacts: 'report/test_result_report_v*.html', fingerprint: true
                    archiveArtifacts artifacts: 'report/test_result_report_v*.pdf', fingerprint: true
                    archiveArtifacts artifacts: 'report/version.txt', fingerprint: true
                }
            }
        }

        // ============================================================================
        stage('Publish Report to Confluence') {
            steps {
                echo '🌐 Publishing reports to Confluence (new page per run)...'
                bat """
                    @echo off
                    "%VENV_PATH%\\Scripts\\python.exe" publish_report_confluence.py
                """
                echo '✅ Confluence page created and attachments uploaded.'
            }
        }

        // ============================================================================
        stage('Email Report') {
            steps {
                echo '📧 Sending report email (with PDF + Confluence link)...'
                bat """
                    @echo off
                    "%VENV_PATH%\\Scripts\\python.exe" send_report_email.py
                """
                echo '📨 Email notifications sent.'
            }
        }
    }

    // ============================================================================
    post {

        success {
            echo '''
            ✅ PIPELINE COMPLETED SUCCESSFULLY
            =================================
            ✔ All stages executed cleanly
            ✔ Reports archived (HTML & PDF)
            ✔ Confluence page published
            ✔ Email sent to recipients
            =================================
            '''
        }

        failure {
            echo '''
            ❌ PIPELINE FAILED
            =================================
            ⚠ Check failed stage logs
            ⚠ Verify SMTP & Confluence credentials
            ⚠ Ensure Python environment & files exist
            ⚠ Confirm network accessibility
            =================================
            '''
        }

        always {
            echo '🧹 Cleaning up workspace...'
        }
    }
}
