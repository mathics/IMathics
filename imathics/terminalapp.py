import mathics


def main():
    from subprocess import call
    call(['jupyter', 'console', '--kernel', 'mathics',
          '--ZMQTerminalInteractiveShell.banner1=' + mathics.version_string,
          '--ZMQTerminalInteractiveShell.banner2=' + mathics.license_string,
         ])

if __name__ == '__main__':
    main()
