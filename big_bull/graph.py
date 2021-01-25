def _arg_names(func):
    return func.__code__.co_varnames[: func.__code__.co_argcount]


async def inject_func(func, injectables, *extra_args, **extra_kwargs):
    inj = {x: injectables[x] for x in _arg_names(func) if x not in extra_kwargs.keys()}
    args = {key: value.get_value() for key, value in inj.items()}
    try:
        for i in inj.values():
            await i.enter()
        value = await func(*extra_args, **extra_kwargs, **args)
    finally:
        for i in inj.values():
            await i.exit()
    return value


def get_arguments_to_inject(func, injectables, ignore_args=[]):
    args = _arg_names(func)
    ret = {}
    for arg in args:
        if arg in ignore_args:
            continue
        if arg not in injectables:
            raise Exception(f"Could not resolve argument {arg} in graph")
        ret[arg] = injectables[arg]
    return ret
