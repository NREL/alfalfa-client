"""
****************************************************************************************************
:copyright (c) 2008-2021 URBANopt, Alliance for Sustainable Energy, LLC, and other contributors.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions
and the following disclaimer in the documentation and/or other materials provided with the
distribution.

Neither the name of the copyright holder nor the names of its contributors may be used to endorse
or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
****************************************************************************************************
"""

import concurrent.futures
import functools
import shutil
import tempfile
from functools import partial
from pathlib import Path
from typing import List


def parallelize(func):

    def parallel_call(func, iter_vals: List, args: List = [], kwargs: dict = {}):
        responses = [None] * len(iter_vals)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_index = {executor.submit(func, iter_vals[i], *args, **kwargs): i for i in range(len(iter_vals))}
            for future in concurrent.futures.as_completed(future_to_index):
                arg = future_to_index[future]

                responses[arg] = future.result()
        return responses

    @functools.wraps(func)
    def parallel_wrapper(self, val, *args, **kwargs):
        if isinstance(val, list):
            return parallel_call(partial(func, self), val, args, kwargs)
        else:
            return func(self, val, *args, **kwargs)

    return parallel_wrapper


def create_zip(model_dir):
    zip_file_fd, zip_file_path = tempfile.mkstemp(suffix='.zip')
    zip_file_path = Path(zip_file_path)
    shutil.make_archive(zip_file_path.parent / zip_file_path.stem, "zip", model_dir)

    return zip_file_path


def prepare_model(model_path) -> str:
    model_path = Path(model_path)
    if (model_path).is_dir():
        return str(create_zip(str(model_path.absolute())))
    else:
        return str(model_path.absolute())


class AlfalfaException(Exception):
    """Wrapper for exceptions which come from alfalfa"""


class AlfalfaWorkerException(AlfalfaException):
    """Wrapper for exceptions from the alfalfa worker"""


class AlfalfaAPIException(AlfalfaException):
    """Wrapper for API errors"""


class AlfalfaClientExcpetion(AlfalfaException):
    """Wrapper for exceptions in client operation"""
