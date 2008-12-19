import commands
import logging

def system(*args):
    cmd = ' '.join(args)
    logging.debug('[system] %s' % cmd)

    status = commands.getstatusoutput(cmd)
    logging.debug('[system][out] %d: %s' % status)

    return status

