import threading


def spy(*ignore):
    """
    Make sure to ignore callables that are more than just their __call__
    because this will destroy everything else.
    """
    def inner(cls):
        class Spy(cls):
            def __getattribute__(self, name):
                attribute = super().__getattribute__(name)
                if hasattr(attribute, '__call__') and name not in ignore:

                    def mark(self, marker):
                        print('{marker} '
                              '>Thread Id 0x{thread_id:012x}< '
                              '{repr} '
                              '{marker} '
                              '{name}()'.format(
                                marker=marker,
                                repr='<{cls} object at 0x{id:012x}>'.format(
                                    cls=type(self).__bases__[0].__name__,
                                    id=id(self)
                                ),
                                name=name,
                                thread_id=threading.get_ident()
                        ))

                    def report(*args, **kwargs):
                        mark(self, ' +')
                        result = attribute(*args, **kwargs)
                        mark(self, '- ')

                        return result

                    return report
                else:
                    return attribute

        return Spy

    return inner
