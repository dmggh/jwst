from . import config
# comes from pyetc.etc_web.config

if __name__ == '__main__' :
    #
    # this mechanism prints the parameters we are interested in as shell
    # commands to set those variables
    #
    # for sh:
    #   python install_params.py name name name > tmp
    #   . tmp
    #
    # for csh:
    #   python install_params.py -csh name name name > tmp
    #   source tmp
    #
    import sys 

    l = sys.argv[1:]

    separator='='

    if len(l) > 0 and l[0] == '-csh' :
        setcmd="set "
        l = l[1:]
    else :
        setcmd=""

    def print_var(xx) :
        print(setcmd+xx+"='"+str(config.__dict__[xx])+"'")

    if len(l) == 0 :
        for x in config.__dict__ :
            if not x.startswith('_') :
                print_var(x)
    else :
        for x in l :
            if x in config.__dict__ :
                print_var(x)
