from src.utils.util import dotdict


def add_to(destination, item):
    return lambda: destination.addItem(item)


def remove_from(source, item):
    return lambda: source.removeItem(item)


Actions = dotdict({
    'addTo': add_to,
    'removeFrom': remove_from
})
