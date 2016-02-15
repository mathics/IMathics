import mathics

banner1 = mathics.version_string
banner2 = mathics.license_string

def main():
    from subprocess import call
    call(['jupyter', 'console', '--kernel', 'mathics',
          '--ZMQTerminalInteractiveShell.banner1=' + banner1,
          '--ZMQTerminalInteractiveShell.banner2=' + banner2,
         ])

if __name__ == '__main__':
    main()
