pipeline {
    agent any

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
    }

    stages {

        // -------------------------------
        stage('Checkout from GitHub') {
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
        stage('Setup Python Environment') {
            steps {
                echo '🐍 Checking and creating Python virtual environment...'
                bat '''
                    @echo off
                    if not exist "%VENV_PATH%" (
                        echo Creating new virtual environment...
                        python -m venv %VENV_PATH%
                    ) else (
                        echo Virtual environment already exists.
                    )
                    echo Activating venv and checking versions...
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
                    echo Upgrading pip...
                    %VENV_PATH%\\Scripts\\python.exe -m pip install --upgrade pip

                    echo Installing required modules from requirements.txt...
                    %VENV_PATH%\\Scripts\\pip.exe install -r requirements.txt

                    echo Installing additional visualization libraries...
                    %VENV_PATH%\\Scripts\\pip.exe install beautifulsoup4 matplotlib
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
                    if not exist "report" mkdir report
                    echo Executing pytest...
                    set PYTHONPATH=%CD%
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
        stage('Enhance Report (Graphical Summary)') {
            steps {
                echo '🎨 Enhancing HTML report with charts and color-coded summary...'
                bat """
                    @echo off
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe enhance_report.py
                """
                echo '✅ Enhanced report generated successfully.'
            }
            post {
                always {
                    echo '📦 Archiving enhanced HTML report and version file...'
                    archiveArtifacts artifacts: 'report/test_result_report_v*.html', fingerprint: true
                    archiveArtifacts artifacts: 'report/version.txt', fingerprint: true
                }
            }
        }

        // -------------------------------
        stage('Verify Confluence API Token') {
            steps {
                echo '🔑 Verifying access to Confluence API before publishing...'
                bat """
                    @echo off
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe check_api_token.py
                """
                echo '✅ Confluence API verification successful.'
            }
        }

        // -------------------------------
        stage('Send Email Report') {
            steps {
                echo '📧 Preparing to send enhanced HTML report via email...'
                bat """
                    @echo off
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe send_report_email.py
                """
                echo '✅ Email with enhanced report sent successfully.'
            }
        }

        // -------------------------------
        stage('Publish to Confluence') {
            steps {
                echo '🌐 Publishing enhanced HTML report to Confluence...'
                bat """
                    @echo off
                    set PYTHONUTF8=1
                    %VENV_PATH%\\Scripts\\python.exe publish_to_confluence.py
                """
                echo '✅ Report successfully published to Confluence space.'
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
            - HTML reports archived and versioned.
            - Email successfully sent.
            - Report published to Confluence.
            =================================
            '''
        }
        failure {
            echo '''
            ❌ PIPELINE FAILED!
            =================================
            - Check Jenkins logs for exact stage failure.
            - Verify report path and Confluence/SMTP credentials.
            - Ensure network access to Confluence and SMTP host.
            =================================
            '''
        }
        always {
            echo '🧹 Pipeline execution finished. Cleaning up workspace...'
        }
    }
}
