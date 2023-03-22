import sys
import traceback
import unittest
from tempfile import gettempdir
from os.path import join, exists
from os import mkdir, remove
from glob import glob


class TestHelper:
    def __init__(self, test_name: str, temp_folder_name: str = 'test_helper', verbose=False):
        self.test_name = test_name
        self._temp_folder_name = temp_folder_name
        self._verbose = verbose

        self.create_temp_folder()
        self.create_temp_folder(self.test_name)

    @property
    def temp_foldername(self):
        return self.make_temp_foldername(self.test_name)

    def make_temp_foldername(self, folder=None):
        if not folder:
            return join(gettempdir(), self._temp_folder_name)

        return join(gettempdir(), self._temp_folder_name, folder)

    def make_temp_filename(self, foldername: str, filename: str):
        return join(self.make_temp_foldername(foldername), filename)

    def create_temp_folder(self, folder=None):
        folder_name = self.make_temp_foldername(folder)
        if self._verbose:
            print(f'TestHelper.create_temp_folder({folder}): {folder_name}')

        if not exists(folder_name):
            mkdir(folder_name)

    def write_file(self, folder: str, filename: str, text: str):
        full_path = self.make_temp_filename(folder, filename)
        with open(full_path, 'w') as f:
            f.write(text)
        return full_path

    def remove_temp_files(self, extension: str):
        files = glob(self.make_temp_filename(
            self.test_name, extension), recursive=True)
        if self._verbose:
            [print(f'remove {f}') for f in files]
        [remove(f) for f in files]

    def print_banner(self, test_case):
        if self._verbose:
            print(f'============== {test_case.id()}')


class TestCaseFactoryMixin:
    def _init_factory(self):
        factory_types = [x for x in type(
            self).mro() if x.__name__.endswith('Factory')]
        # print(factory_types)

        factory_type = factory_types[0] if factory_types else None

        if factory_type:
            factory_name = factory_type.__module__ + '.' + factory_type.__name__
            factory_type.__init__(self)

            self.factory_foldername = self._helper.make_temp_foldername(
                factory_name.replace('.', '_'))
            self._helper.create_temp_folder(self.factory_foldername)


class TestCaseBase(unittest.TestCase, TestCaseFactoryMixin):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self._helper = TestHelper(test_name=self.testName, verbose=False)
        self._init_factory()

    @ property
    def tempFolder(self) -> str:
        return self._helper.temp_foldername

    @ property
    def testName(self) -> str:
        return self.id().replace('.', '_')

    def setUp(self) -> None:
        self._helper.print_banner(test_case=self)

        [self._helper.remove_temp_files(x) for x in (
            '*.c', '*.h', '*.so', '*.i', '*.o')]
        return unittest.TestCase.setUp(self)

    def writeFile(self, filename: str, text: str) -> str:
        return self._helper.write_file(self.testName, filename=filename, text=text)


# foss: based on https://stackoverflow.com/questions/4319825/python-unittest-opposite-of-assertraises
is_micropython = sys.implementation.name == "micropython"

if is_micropython:
    from unittest import AssertRaisesContext

    class AssertDoesNotRaiseContext(AssertRaisesContext):
        def __exit__(self, exc_type, exc_value, tb):
            self.exception = exc_value
            if exc_type is not None:
                assert False, "%r raised (%r expected)" % (
                    exc_type, self.expected)

            return True

    class MicropythonAssertMixin:
        def assertCountEqual(self, first, second, msg=None):
            x = len(first)
            y = len(second)
            if not msg:
                msg = "%r vs (expected) %r" % (x, y)
            assert x == y, msg

        def assertTupleEqual(self, first, second, msg=None):
            assert isinstance(first, tuple)
            assert isinstance(second, tuple)

            x = first
            y = second
            if not msg:
                msg = "%r vs (expected) %r" % (x, y)
            assert x == y, msg

        def assertListEqual(self, first, second, msg=None):
            assert isinstance(first, list)
            assert isinstance(second, list)

            x = first
            y = second
            if not msg:
                msg = "%r vs (expected) %r" % (x, y)
            assert x == y, msg

        def assertSequenceEqual(self, first, second, msg=None):
            assert isinstance(first, list) or isinstance(first, tuple)
            assert isinstance(second, list) or isinstance(second, tuple)
            assert type(first) == type(
                second), f"sequences are different types ({type(first)}, {type(second)}"

            x = first
            y = second
            if not msg:
                msg = "%r vs (expected) %r" % (x, y)
            assert x == y, msg

        def assertDoesNotRaise(self, func=None, *args, **kwargs):
            if func is None:
                return AssertDoesNotRaiseContext(BaseException)

            try:
                func(*args, **kwargs)
            except Exception as e:
                assert False, f"exception '{e}' raised"

        def assertRaisesAny(self, func=None, *args, **kwargs):
            if func is None:
                return AssertRaisesContext(BaseException)

            try:
                func(*args, **kwargs)
            except Exception as e:
                return

            assert False, "exception not raised" % exc

else:
    from unittest.case import _AssertRaisesContext

    class _AssertDoesNotRaiseContext(_AssertRaisesContext):
        def __exit__(self, exc_type, exc_value, tb):
            if exc_type is not None:
                self.exception = exc_value.with_traceback(None)

                try:
                    exc_name = self.expected.__name__
                except AttributeError:
                    exc_name = str(self.expected)

                if self.obj_name:
                    self._raiseFailure("{} raised by {}".format(exc_name,
                                                                self.obj_name))
                else:
                    self._raiseFailure("{} raised".format(exc_name))

            else:
                traceback.clear_frames(tb)

            return True

    class AssertRaisesMixin:
        # todo foss: get this to override assertRaises
        def assertRaisesAny(self, *args, **kwargs):
            context = _AssertRaisesContext(BaseException, self)
            try:
                return context.handle('assertRaises', args, kwargs)
            finally:
                context = None

    class AssertDoesNotRaiseMixin:
        def assertDoesNotRaise(self, expected_exception=BaseException, *args, **kwargs):
            context = _AssertDoesNotRaiseContext(expected_exception, self)
            try:
                return context.handle('assertDoesNotRaise', args, kwargs)
            finally:
                context = None

if is_micropython:
    class TestCase(TestCaseBase, MicropythonAssertMixin):
        pass
else:
    class TestCase(TestCaseBase, AssertRaisesMixin, AssertDoesNotRaiseMixin):
        pass
