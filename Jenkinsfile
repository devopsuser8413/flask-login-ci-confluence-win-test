pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {

        // ============================
        // SMTP
        // ============================
        SMTP_HOST        = credentials('smtp-host')
        SMTP_PORT        = '587'
        SMTP_USER        = credentials('smtp-user')
        SMTP_PASS        = credentials('smtp-pass')
        REPORT_FROM      = credentials('sender-email')
        REPORT_TO        = credentials('receiver-email')
        REPORT_CC        = credentials('cc-email')
        REPORT_BCC       = credentials('bcc-email')

        // ============================
        // Confluence
        // ============================
        CONFLUENCE_BASE  = credentials('confluence-base')
        CONFLUENCE_USER  = credentials('confluence-user')
        CONFLUENCE_TOKEN = credentials('confluence-token')
        CONFLUENCE_SPACE = 'DEMO'
        CONFLUENCE_TITLE = 'Test Result Report'

        // ============================
        // Confluence
        // ============================
        JIRA_URL     = credentials('jira-url')         // stored as secret text
        JIRA_USER    = credentials('jira-user')        // stored as username
        RTM_API_KEY  = credentials('jira-api-token')   // stored as secret text
        JIRA_PROJECT = credentials('jira-project')     // stored as secret text

        // ============================
        // GitHub
        // ============================
        GITHUB_CREDENTIALS = credentials('github-credentials')

        // ============================
        // Report
        // ============================
        REPORT_PATH   = 'report/report.html'
        REPORT_DIR    = 'report'
        VERSION_FILE  = 'report/version.txt'

        // ============================
        // Python Setup
        // ============================
        VENV_PATH     = "C:\\jenkins_home\\python_venvs\\flask_venv"
        PIP_CACHE_DIR = "C:\\jenkins_home\\pip-cache"

        PYTHONUTF8     = '1'
        PYTHONIOENCODING = 'utf-8'
        PYTHONLEGACYWINDOWSSTDIO = '1'
    }

    stages {

        // ------------------------------
        stage('Setup Encoding') {
            steps {
                echo 'Setting UTF-8 encoding...'
                bat """
                    @echo off
                    chcp 65001 >nul
                """
            }
        }

        // ------------------------------
        stage('Checkout GitHub') {
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

                echo 'Checkout complete.'
            }
        }

        // ------------------------------
        stage('Setup Python') {
            steps {
                echo "Ensuring Python virtual environment exists..."

                // REUSE VENV → DO NOT DELETE ANYMORE
                bat """
                    @echo off

                    if not exist "%VENV_PATH%" (
                        echo Creating new venv...
                        python -m venv "%VENV_PATH%"
                    )

                    "%VENV_PATH%\\Scripts\\python.exe" -m pip install --upgrade pip setuptools wheel ^
                        --cache-dir "%PIP_CACHE_DIR%"
                """
            }
        }

        // ------------------------------
        stage('Install Dependencies') {
            steps {
                echo 'Installing dependencies...'
                bat """
                    @echo off

                    if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%"

                    rem === Install only when requirements changed ===
                    if exist requirements.lock (
                        fc requirements.txt requirements.lock >nul
                        if %errorlevel%==0 (
                            echo Requirements unchanged. Skipping pip install.
                            exit /b 0
                        )
                    )

                    echo Installing dependencies...
                    "%VENV_PATH%\\Scripts\\pip.exe" install ^
                        --prefer-binary ^
                        --cache-dir "%PIP_CACHE_DIR%" ^
                        -r requirements.txt

                    copy /Y requirements.txt requirements.lock >nul
                """
            }
        }

        // ------------------------------
        stage('Run Tests') {
            steps {
                echo 'Running tests...'
                bat """
                    @echo off
                    if not exist "report" mkdir report

                    "%VENV_PATH%\\Scripts\\python.exe" -m pytest ^
                        --html=%REPORT_PATH% ^
                        --self-contained-html ^
                        > report\\pytest_output.txt 2>&1 || exit /b 0
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'report/report.html', fingerprint: true
                }
            }
        }

        // ------------------------------
        stage('Generate Report') {
            steps {
                bat """
                    "%VENV_PATH%\\Scripts\\python.exe" generate_report.py
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'report/test_result_report_v*.html', fingerprint: true
                    archiveArtifacts artifacts: 'report/test_result_report_v*.pdf', fingerprint: true
                    archiveArtifacts artifacts: 'report/version.txt', fingerprint: true
                }
            }
        }

        // ------------------------------
        stage('Publish Report to Confluence') {
            steps {
                bat """
                    timeout /t 2 >nul
                    "%VENV_PATH%\\Scripts\\python.exe" publish_report_confluence.py
                """
            }
        }

        // ------------------------------
        stage('Email Report') {
            steps {
                bat """
                    "%VENV_PATH%\\Scripts\\python.exe" send_report_email.py
                """
            }
        }

    //     stage('Upload to Jira RTM') {
    //         steps {
    //             bat """
    //             "%VENV_PATH%\\Scripts\\python.exe upload_to_jira.py
    //             """
    //         }
    //     }

    //     stage('RTM Integration') {
    //         steps {
    //             bat """
    //             "%VENV_PATH%\\Scripts\\python.exe rtm_autogenerate_from_pytest.py
    //             """
    //         }
    //     }
    }

    post {
        success {
            echo 'PIPELINE COMPLETED SUCCESSFULLY'
        }
        failure {
            echo 'PIPELINE FAILED — Check logs!'
        }
        always {
            echo 'Cleaning workspace complete.'
        }
    }
}
