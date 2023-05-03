from john import TestCase
from crelm import Factory
import importlib
import os.path

class TddState:
    def __init__(self, module_name:str):
        self._module_name = module_name

        self.reset()

    def reset(self):
        self.tube = None
        self.sut = None
        self.externs = []

    def _ensure_tube(self) -> None:
        if not self.tube:
            self.sut = None

            test_case_module = importlib.import_module(self._module_name)
            test_case_filename = test_case_module.__file__
            test_case_name = os.path.splitext(
                os.path.basename(test_case_filename))[0]

            c_filename = f'{test_case_name}.c'
            h_filename = f'{test_case_name}.h'

            self.tube = Factory().create_Tube(test_case_name) \
                .set_source_folder_relative(test_case_filename) \
                .add_source_file(c_filename) \
                .add_header_file(h_filename) \
                .add_externs(self.externs)
            
            return self.tube

    def ensure_sut(self):
        if not self.sut:
            self.sut = self._ensure_tube().squeeze()

        return self.sut

class Tdd(TestCase):

    @staticmethod
    def go():
        Tdd.Runner.run()

    @classmethod
    def setUpClass(clazz) -> None:
        clazz._state = TddState(clazz.__module__)
        return super().setUpClass()

    @classmethod
    def tearDownClass(clazz) -> None:
        clazz._state = None
        return super().tearDownClass()

    def setUpMocks(self):
        pass

    def setUp(self):
        super().setUp()
        self.setUpMocks()

    @property
    def _state(self):
        return self.__class__._state

    @property
    def sut(self):
        return self._state.ensure_sut()
    
    def register_mock(self, sig:str) -> None:
        if not self._state.sut:
            self._state.externs.append(sig)

    def attach_mock(self, func):
        def_extern_decorator = self._state.tube._ffi.def_extern()
        def_extern_decorator(func)
        return getattr(self._state.tube._lib, func.__name__)
