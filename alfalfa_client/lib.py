# ****************************************************************************************************
# :copyright (c) 2008-2021 URBANopt, Alliance for Sustainable Energy, LLC, and other contributors.

# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:

# Redistributions of source code must retain the above copyright notice, this list of conditions
# and the following disclaimer.

# Redistributions in binary form must reproduce the above copyright notice, this list of conditions
# and the following disclaimer in the documentation and/or other materials provided with the
# distribution.

# Neither the name of the copyright holder nor the names of its contributors may be used to endorse
# or promote products derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ****************************************************************************************************

import concurrent.futures
import functools
import json
import shutil
import tempfile
from functools import partial
from os import PathLike, path
from pathlib import Path
from typing import List

from requests import Response


def parallelize(func):
    """Parallelize a function
    Decorator which, when applied to a function, will parallelize the function
    on the first non-self parameter. If a list is passed n instances of the
    original function will be called inside Threads. The results will be returned
    as a list with the same order as the original. If a list is not passed, the
    original function will be called.

    """

    def parallel_call(func, iter_vals: List, args: List = [], kwargs: dict = {}):
        responses = [None] * len(iter_vals)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_index = {executor.submit(func, iter_vals[i], *args, **kwargs): i for i in range(len(iter_vals))}
            for future in concurrent.futures.as_completed(future_to_index):
                arg = future_to_index[future]

                responses[arg] = future.result()
        return responses

    @functools.wraps(func)
    def parallel_wrapper(self, *args, **kwargs):
        # Find the first parameter as either an arg or kwarg
        if len(args) > 0:
            val = args[0]
            args = args[1:]
        else:
            first_varname = func.__code__.co_varnames[1]
            if first_varname in kwargs.keys():
                val = kwargs[first_varname]
                del kwargs[first_varname]
            else:
                raise TypeError(f"{func.__name__}() missing 1 required positional argument: '{first_varname}'")

        if isinstance(val, list):
            return parallel_call(partial(func, self), val, args, kwargs)
        else:
            return func(self, val, *args, **kwargs)

    return parallel_wrapper


def create_zip(dir: PathLike) -> str:
    """Create Zip
    Takes a directory and creates a temporary zip file of it.

    :param dir: directory to create zip of

    :returns: path of zip file
    """
    zip_file_fd, zip_file_path = tempfile.mkstemp(prefix=path.basename(dir), suffix='.zip')
    zip_file_path = Path(zip_file_path)
    shutil.make_archive(str(zip_file_path.parent / zip_file_path.stem), "zip", None, str(dir))

    return zip_file_path


def prepare_model(model_path: PathLike) -> str:
    """Prepares model for upload
    Takes a file or directory. If the input is a file it returns the file.
    If the input is a directory it zips the directory and returns the path to that zip.

    :param model_path: path to model

    :returns: path of prepared model
    """
    model_path = Path(model_path)
    if model_path.is_dir():
        return str(create_zip(str(model_path.absolute())))
    else:
        return str(model_path.absolute())


class AlfalfaException(Exception):
    """Wrapper for exceptions which come from alfalfa"""


class AlfalfaWorkerException(AlfalfaException):
    """Wrapper for exceptions from the alfalfa worker"""


class AlfalfaAPIException(AlfalfaException):
    """Wrapper for API errors"""

    def __init__(self, response: Response, *args: object) -> None:
        self.response = response
        body = response.json()
        super().__init__(body["message"], *args)

        if "payload" in body:
            self.payload = json.dumps(body["payload"])

    def __str__(self) -> str:
        if hasattr(self, "payload"):
            return super().__str__() + '\nAPI Payload: \n' + json.dumps(self.payload)
        return super().__str__()


class AlfalfaClientException(AlfalfaException):
    """Wrapper for exceptions in client operation"""
