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

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from app_edge_single_fragment import AppEdgeSingleFragment
from holoscan.schedulers import MultiThreadScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description="H.264 endoscopy tool tracking application.")
    parser.add_argument("-d", "--data", type=str, help="Path to the data directory")
    parser.add_argument("-c", "--config", type=str, help="Path to the configuration file")
    args = parser.parse_args()
    return args.data, args.config


def parse_config(config_path):
    fragment_mode = False
    benchmarking = False
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
            application = config.get("application", {})
            fragment_mode = application.get("multifragment", False)
            benchmarking = application.get("benchmarking", False)
    except Exception as e:
        logger.error(f"Error parsing configuration file: {e}")
    return fragment_mode, benchmarking


def main():
    data_directory, config_path = parse_arguments()

    if not data_directory:
        data_directory = os.getenv("HOLOSCAN_INPUT_PATH")
        if not data_directory or not os.path.isdir(data_directory):
            data_directory = Path.cwd() / "data" / "endoscopy"
            if not data_directory.is_dir():
                logger.error(
                    "Input data not provided. Use --data or set HOLOSCAN_INPUT_PATH environment variable."
                )
                sys.exit(-1)

    if not config_path:
        config_path = os.getenv("HOLOSCAN_CONFIG_PATH")
        if not config_path:
            config_path = Path(sys.argv[0]).parent.parent / "endoscopy_tool_tracking.yaml"

    fragment_mode, benchmarking = parse_config(config_path)

    if fragment_mode:
        # logger.info("Running application in multi-fragment mode")
        # app = AppEdgeMultiFragment(data_directory)
        pass
    else:
        logger.info("Running application in single fragment mode")
        app = AppEdgeSingleFragment(data_directory)

    if benchmarking:
        logger.info("Benchmarking enabled")
        trackers = app.track_distributed() if fragment_mode else app.track()

    app.config(str(config_path))
    app.scheduler(
        MultiThreadScheduler(
            app,
            worker_thread_number=5,
            check_recession_period_ms=0.0,
            stop_on_deadlock=True,
            stop_on_deadlock_timeout=500,
            name="multithread_scheduler",
        )
    )
    app.run()

    if benchmarking:
        if fragment_mode:
            for name, tracker in trackers.items():
                logger.info(f"Fragment: {name}")
                tracker.logger.info()
        else:
            trackers.logger.info()


if __name__ == "__main__":
    main()
