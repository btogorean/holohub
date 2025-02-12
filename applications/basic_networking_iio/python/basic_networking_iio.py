# SPDX-FileCopyrightText: Copyright (c) 2022-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
import sys
from pathlib import Path

from holoscan.conditions import CountCondition
from holoscan.core import Application, Operator, OperatorSpec

from holohub.basic_network import BasicNetworkOpRx, BasicNetworkOpTx

logger = logging.getLogger("BasicNetworkingIIO")
logging.basicConfig(level=logging.INFO)

class BasicNetworkIIORxOp(Operator):
    def __init__(self, fragment, *args, **kwargs):
        self.count = 1
        # Need to call the base class constructor last
        super().__init__(fragment, *args, **kwargs)

    def setup(self, spec: OperatorSpec):
        spec.input("msg_in")

    def compute(self, op_input, op_output, context):
        value = op_input.receive("msg_in")
        data = list(value.data)
        logger.info(f"Rx message received (count: {self.count}, size: {len(data)}")
        newFileBytes = bytes(data)
        f = open("file.txt", "ab")
        f.write(newFileBytes)
        f.close()
        self.count += 1


# Now define a simple application using the operators defined above
NUM_MSGS = 5000


class App(Application):
    def compose(self):
        if len(self.kwargs("network_rx")) > 0:
            basic_net_rx = BasicNetworkOpRx(self, name="basic_net_rx", **self.kwargs("network_rx"))
            rx = BasicNetworkIIORxOp(self, CountCondition(self, NUM_MSGS), name="rx")
            self.add_flow(basic_net_rx, rx, {("burst_out", "msg_in")})
        else:
            logger.info("No RX config found")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error(
            "Must specify configuration file as second argument. "
            "If using the 'run' script, use --extra_args <config_name>"
        )
        sys.exit(-1)

    config_path = sys.argv[1]
    if not Path(config_path).is_file():
        logger.error(f"Configuration file {config_path} not found")
        sys.exit(-2)

    app = App()
    app.config(config_path)
    app.run()
