from big_bull import graph
import logging

logger = logging.getLogger("big_bull.init")

_inject_registry = []
_init_registry = []

injectables = None
creating_providers_complete = False


class Injectable:
    def __init__(self, func):
        self.func = func
        self.value = None

    @property
    def args(self):
        return self.func.__code__.co_varnames[: self.func.__code__.co_argcount]

    @property
    def name(self):
        return self.func.__name__

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    async def enter(self):
        pass

    async def exit(self):
        pass


class Func(Injectable):
    pass


class ContextManager(Injectable):
    async def enter(self):
        return await self.value.__aenter__()

    async def exit(self):
        return await self.value.__aexit__()


def init(func):
    def wrapper():
        func()

    _init_registry.append(Func(func))
    return wrapper


def inject(func):
    async def wrapper(*args, **kwargs):
        if not creating_providers_complete:
            raise Exception(
                "Cannot call injected functions before initialization is complete"
            )
        return await graph.inject_func(func, injectables, *args, **kwargs)

    return wrapper


def provide(func):
    def wrapper():
        func()

    _inject_registry.append(Func(func))
    return wrapper


def provide_ctx(func):
    def wrapper():
        func()

    _inject_registry.append(ContextManager(func))
    return wrapper


class Node:
    def __init__(self, name):
        self.name = name
        self.edges = []
        self.injectable = None

    def add_edge(self, node):
        self.edges.append(node)

    def add_injectable(self, injectable):
        self.injectable = injectable

    def __repr__(self):
        return f"{self.name}(edges={self.edges} func={self.func})"


def dep_resolve(node, resolved, seen=[]):
    seen.append(node)
    for edge in node.edges:
        if edge not in resolved:
            if edge in seen:
                raise Exception(
                    "Circular reference detected: %s -> %s" % (node.name, edge.name)
                )
        dep_resolve(edge, resolved, seen)
    resolved.append(node)


def get_or_set(name, dict_, default):
    if name in dict_:
        ret = dict_[name]
    else:
        ret = default
        dict_[name] = ret
    return ret


async def run_init_tasks():
    nodes = {}
    logger.info("Initializing provider nodes...")
    for task in _inject_registry:
        args = task.args
        name = task.name
        node = get_or_set(name, nodes, Node(name))
        node.add_injectable(task)
        for arg in args:
            node.add_edge(get_or_set(arg, nodes, Node(arg)))
    resolved = []
    if not len(nodes):
        return nodes
    logger.info("Resolve dependencies...")
    dep_resolve(nodes[next(iter(nodes))], resolved)
    global injectables
    injectables = {}
    logger.info("Resolving provider arguments...")
    for r in resolved:
        value = await graph.inject_func(r.injectable.func, injectables)
        r.injectable.set_value(value)
        injectables[r.name] = r.injectable
    global creating_providers_complete
    creating_providers_complete = True
    logger.info("Running initializers...")
    for init in _init_registry:
        await graph.inject_func(init.func, injectables)
    return injectables
