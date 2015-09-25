import os
import platform

from arctasks import *
from arctasks.django import manage

@arctask(configured="dev", timed=True)
def init(ctx, overwrite=False):
    virtualenv(ctx, overwrite=overwrite)
    install(ctx)
    createdb(ctx, drop=overwrite)
    manage(ctx, 'migrate')
    manage(ctx, 'rebuild_index --clopen --noinput')
    manage(ctx, 'collectstatic --noinput')
    manage(ctx, 'loaddata dummy_user.json category.json severity.json species.json counties.json pages.json')
    manage(ctx, 'test')
