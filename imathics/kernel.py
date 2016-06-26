import sys
import traceback

from ipykernel.kernelbase import Kernel
from ipykernel.comm import CommManager

from mathics.core.definitions import Definitions
from mathics.core.evaluation import Evaluation, Message, Result
from mathics.core.expression import Integer
from mathics.core.parser import IncompleteSyntaxError, TranslateError, MultiLineFeeder
from mathics.core.parser.util import parser
from mathics.core.parser.tokeniser import Tokeniser
from mathics.builtin import builtins
from mathics import settings
from mathics.version import __version__
from mathics.doc.doc import Doc


class MathicsKernel(Kernel):
    implementation = 'Mathics'
    implementation_version = '0.1'
    language_info = {
        'version': __version__,
        'name': 'Mathematica',
        'mimetype': 'text/x-mathematica',
    }
    banner = "Mathics kernel"   # TODO

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.definitions = Definitions(add_builtin=True)        # TODO Cache
        self.definitions.set_ownvalue('$Line', Integer(0))  # Reset the line number
        self.establish_comm_manager()  # needed for ipywidgets and Manipulate[]
        self._feeder = MultiLineFeeder('')

    def establish_comm_manager(self):
        self.comm_manager = CommManager(parent=self, kernel=self)
        comm_msg_types = ['comm_open', 'comm_msg', 'comm_close']
        for msg_type in comm_msg_types:
            self.shell_handlers[msg_type] = getattr(self.comm_manager, msg_type)

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        # TODO update user definitions

        response = {
            'payload': [],
            'user_expressions': {},
        }

        evaluation = Evaluation(self.definitions, result_callback=self.result_callback,
                                out_callback=self.out_callback, clear_output_callback=self.clear_output_callback,
                                display_data_callback=self.display_data_callback)
        try:
            results = evaluation.parse_evaluate(code, timeout=settings.TIMEOUT)
        except Exception as exc:
            # internal error
            response['status'] = 'error'
            response['ename'] = 'System:exception'
            response['traceback'] = traceback.format_exception(*sys.exc_info())
            results = []
        else:
            response['status'] = 'ok'
        response['execution_count'] = self.definitions.get_line_no()
        return response

    def out_callback(self, out):
        if out.is_message:
            content = {
                'name': 'stderr',
                'text': '{symbol}::{tag}: {text}\n'.format(**out.get_data()),
            }
        elif out.is_print:
            content = {
                'name': 'stdout',
                'text': out.text + '\n',
            }
        else:
            raise ValueError('Unknown out')
        self.send_response(self.iopub_socket, 'stream', content)

    def result_callback(self, result):
        content = {
            'execution_count': result.line_no,
            'data': result.data,
            'metadata': result.metadata,
        }
        self.send_response(self.iopub_socket, 'execute_result', content)

    def clear_output_callback(self, wait=False):
        # see http://jupyter-client.readthedocs.org/en/latest/messaging.html
        content = dict(wait=wait)
        self.send_response(self.iopub_socket, 'clear_output', content)

    def display_data_callback(self, result):
        # see http://jupyter-client.readthedocs.org/en/latest/messaging.html
        content = {
            'data': result.data,
            'metadata': result.metadata,
        }
        self.send_response(self.iopub_socket, 'display_data', content)

    def do_inspect(self, code, cursor_pos, detail_level=0):
        start_pos, end_pos, name = self.find_symbol_name(code, cursor_pos)

        if name is None:
            return {'status': 'error'}

        if '`' not in name:
            name = 'System`' + name

        try:
            instance = builtins[name]
        except KeyError:
            return {'status': 'ok', 'found': False, 'data': {}, 'metadata': {}}

        doc = Doc(instance.__doc__ or '')
        data = {
            'text/plain': str(doc),
            # TODO latex
            # TODO html
        }
        return {'status': 'ok', 'found': True, 'data': data, 'metadata': {}}

    def do_complete(self, code, cursor_pos):
        start_pos, end_pos, name = self.find_symbol_name(code, cursor_pos)

        if name is None:
            return {'status': 'error'}

        remove_system = False
        system_prefix = 'System`'
        if '`' not in name:
            name = system_prefix + name
            remove_system = True

        matches = []
        for key in builtins:
            if key.startswith(name):
                matches.append(key)

        if remove_system:
            matches = [match[len(system_prefix):] for match in matches]

        return {
            'status': 'ok',
            'matches': matches,
            'cursor_start': start_pos,
            'cursor_end': end_pos,
            'metadata': {},
        }

    def do_is_complete(self, code):
        feeder = MultiLineFeeder(code)
        while not feeder.empty():
            try:
                ast = parser.parse(feeder)
            except IncompleteSyntaxError:
                return {'status': 'incomplete', 'indent': ''}
            except TranslateError:
                return {'status': 'invalid'}
            else:
                return {'status': 'complete'}

    def find_symbol_name(self, code, cursor_pos):
        '''
        Given a string of code tokenize it until cursor_pos and return the final symbol name.
        returns None if no symbol is found at cursor_pos.

        >>> MathicsKernel.find_symbol_name('1 + Sin', 6)
        'System`Sin'

        >>> MathicsKernel.find_symbol_name('1 + ` Sin[Cos[2]] + x', 8)
        'System`Sin'

        >>> MathicsKernel.find_symbol_name('Sin `', 4)
        '''
        feeder = MultiLineFeeder(code)
        tokeniser = Tokeniser(feeder)
        while tokeniser.pos < cursor_pos:
            token = tokeniser.next()
            if token.tag == 'END':
                break
        if token.tag == 'Symbol':
            return token.pos, tokeniser.pos, token.text
        return None, None, None
