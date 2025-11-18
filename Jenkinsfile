pipeline {
    agent any

    options {
        timestamps()   // ANSI color is NOT allowed here
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
        REPORT_CC        = credentials('cc-email')         // optional
        REPORT_BCC       = credentials('bcc-email')        // optional

        // ===========================================
        // 🌐 Confluence Configuration
        // ===========================================
        CONFLUENCE_BASE  = credentials('confluence-base')
        CONFLUENCE_USER  = credentials('confluence-user')
        CONFLUENCE_TOKEN = credentials('confluence-token')
        CONFLUENCE_SPACE = 'DEMO'
        CONFLUENCE_TITLE = 'Test Result Report'

        // ===========================================
        // 🔐 GitHub
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
        // ⚡ PIP Cache
        // ===========================================
        PIP_CACHE_DIR = "C:\\jenkins_home\\pip-cache"
    }

    stages {

        // ----------------------------------------------------------------------
        stage('Enable ANSI Colors') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo "✨ ANSI Color Mode Enabled"
                }
            }
        }

        // ----------------------------------------------------------------------
        stage('Setup Encoding') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '🔧 Setting system encoding to UTF-8...'
                    bat '''
                        @echo off
                        chcp 65001 >nul
                        echo UTF-8 enabled (Code Page 65001)
                    '''
                }
            }
        }

        // ----------------------------------------------------------------------
        stage('Checkout GitHub') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '📦 Checking out source code...'

                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: '*/main']],
                        userRemoteConfigs: [[
                            url: 'https://github.com/devopsuser8413/flask-login-ci-confluence-win-test.git',
                            credentialsId: 'github-credentials'
                        ]]
                    ])

                    echo '✅ Source checkout completed.'
                }
            }
        }

        // ----------------------------------------------------------------------
        stage('Setup Python') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '🐍 Creating Python Virtual Environment...'
                    bat """
                        @echo off

                        if exist "%VENV_PATH%" (
                            echo Removing old Python venv...
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
        }

        // ----------------------------------------------------------------------
        stage('Install Dependencies') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '📦 Installing Python dependencies...'
                    bat """
                        @echo off
                        if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%"

                        "%VENV_PATH%\\Scripts\\pip.exe" install --quiet ^
                            --cache-dir "%PIP_CACHE_DIR%" -r requirements.txt
                    """
                    echo '⚡ Dependencies installed using PIP cache!'
                }
            }
        }

        // ----------------------------------------------------------------------
        stage('Run Tests') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '🧪 Running Tests and Generating Raw HTML Report...'

                    bat """
                        @echo off
                        if not exist "report" mkdir report
                        set PYTHONPATH=%CD%

                        "%VENV_PATH%\\Scripts\\python.exe" -m pytest ^
                            --html=%REPORT_PATH% --self-contained-html ^
                            > report\\pytest_output.txt 2>&1 || exit /b 0
                    """

                    echo '✅ Raw report & pytest_output.txt generated.'
                }
            }

            post {
                always {
                    echo '📤 Archiving Raw HTML...'
                    archiveArtifacts artifacts: 'report/report.html', fingerprint: true
                }
            }
        }

        // ----------------------------------------------------------------------
        stage('Generate Report') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '🎨 Enhancing HTML report and creating PDF...'
                    bat """
                        @echo off
                        "%VENV_PATH%\\Scripts\\python.exe" generate_report.py
                    """
                    echo '📄 PDF + Enhanced HTML generated.'
                }
            }

            post {
                always {
                    echo '📦 Archiving Enhanced Reports...'
                    archiveArtifacts artifacts: 'report/test_result_report_v*.html', fingerprint: true
                    archiveArtifacts artifacts: 'report/test_result_report_v*.pdf', fingerprint: true
                    archiveArtifacts artifacts: 'report/version.txt', fingerprint: true
                }
            }
        }

        // ----------------------------------------------------------------------
        stage('Publish Report to Confluence') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '🌐 Publishing Reports to Confluence...'
                    bat """
                        @echo off
                        "%VENV_PATH%\\Scripts\\python.exe" publish_report_confluence.py
                    """
                    echo '✅ Confluence page created & files uploaded.'
                }
            }
        }

        // ----------------------------------------------------------------------
        stage('Email Report') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '📧 Sending Test Report Email...'
                    bat """
                        @echo off
                        "%VENV_PATH%\\Scripts\\python.exe" send_report_email.py
                    """
                    echo '📨 Email notifications sent.'
                }
            }
        }
    }

    // ----------------------------------------------------------------------
    post {
        success {
            echo '''
            ✅ PIPELINE SUCCESS
            ================================
            ✔ Tests executed successfully
            ✔ Reports enhanced (HTML + PDF)
            ✔ Confluence page created
            ✔ Email delivered
            ================================
            '''
        }

        failure {
            echo '''
            ❌ PIPELINE FAILED
            ================================
            ⚠ Review the failing stage
            ⚠ Check SMTP/Confluence creds
            ⚠ Validate network access
            ================================
            '''
        }

        always {
            echo '🧹 Cleaning workspace complete.'
        }
    }
}
