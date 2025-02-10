# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import signal
import sys
from argparse import ArgumentParser
from pathlib import Path
from queue import Queue

from endoscopy_tool_tracking import EndoscopyToolTrackingPipeline
from grpc_service import GrpcService

from operators.grpc_operators.python.server.application_factory import (
    ApplicationFactory,
    ApplicationInstance,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    logger.warning(f"Caught signal {sig}. Stopping services...")
    grpc_service = GrpcService()
    grpc_service.stop()
    sys.exit(0)


def _create_application_instance(args, request_queue: Queue, response_queue: Queue):
    instance = ApplicationInstance(EndoscopyToolTrackingPipeline(request_queue, response_queue))
    instance.instance.config(str(args.config))
    instance.instance.data_path = args.data
    instance.start_application()
    return instance


def parse_arguments():
    parser = ArgumentParser(description="gRPC-enabled Endoscopy tool tracking demo application.")

    parser.add_argument(
        "-c",
        "--config",
        default=os.environ.get(
            "HOLOSCAN_CONFIG_PATH",
            Path(sys.argv[0]).parent.parent / "endoscopy_tool_tracking.yaml",
        ),
        help=("Set config path to override the default config file location"),
    )
    parser.add_argument(
        "-d",
        "--data",
        default=os.environ.get("HOLOSCAN_INPUT_PATH", default_data_path),
        help=("Set the data path (default: %(default)s)."),
    )
    parser.add_argument(
        "-p",
        "--port",
        default=50051,
        help=("Set the gRPC Server listening port  (default: %(default)s)."),
    )
    return parser.parse_args()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    default_data_path = f"{os.getcwd()}/data/endoscopy"
    args = parse_arguments()

    if not os.path.isdir(args.data):
        raise ValueError(
            f"Data path '{args.data}' does not exist. Use --data or set HOLOSCAN_INPUT_PATH environment variable."
        )

    application_factory = ApplicationFactory()
    application_factory.register_application(
        "EndoscopyToolTracking",
        lambda request_queue, response_queue: _create_application_instance(
            args, request_queue, response_queue
        ),
    )

    grpc_service = GrpcService()
    grpc_service.initialize(args.port, application_factory)
    grpc_service.start()
