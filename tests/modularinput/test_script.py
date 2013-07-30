# Copyright 2011-2013 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from modularinput_testlib import unittest, xml_compare
from splunklib.modularinput.argument import Argument
from splunklib.modularinput.event import Event
from splunklib.modularinput.event_writer import EventWriter
from splunklib.modularinput.script import Script
from splunklib.modularinput.scheme import Scheme

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class ScriptTest(unittest.TestCase):
    def test_error_on_script_with_null_scheme(self):
        """A script that returns a null scheme should generate no output on
        stdout and an error on stderr saying that it the scheme was null."""

        # Override abstract methods
        class NewScript(Script):
            def get_scheme(self):
                return None

            def stream_events(self, inputs, ew):
                # not used
                return
        
        script = NewScript()

        out = StringIO()
        err = StringIO()
        ew = EventWriter(out, err)

        in_stream = StringIO()

        args = ["--scheme"]
        return_value = script.run_script(args, ew, in_stream)

        self.assertEqual("", out.getvalue())
        self.assertEqual("FATAL Modular input script returned a null scheme.\n", err.getvalue())
        self.assertNotEqual(0, return_value)

    def test_scheme_properly_generated_by_script(self):
        """Check that a scheme generated by a script is what we expect."""

        # Override abstract methods
        class NewScript(Script):
            def get_scheme(self):
                scheme = Scheme("abcd")
                scheme.description = u"\uC3BC and \uC3B6 and <&> f\u00FCr"
                scheme.streaming_mode = scheme.streaming_mode_simple
                scheme.use_external_validation = False
                scheme.use_single_instance = True

                arg1 = Argument("arg1")
                scheme.add_argument(arg1)

                arg2 = Argument("arg2")
                arg2.description = u"\uC3BC and \uC3B6 and <&> f\u00FCr"
                arg2.data_type = Argument.data_type_number
                arg2.required_on_create = True
                arg2.required_on_edit = True
                arg2.validation = "is_pos_int('some_name')"
                scheme.add_argument(arg2)

                return  scheme

            def stream_events(self, inputs, ew):
                # not used
                return

        script = NewScript()

        out = StringIO()
        err = StringIO()
        ew = EventWriter(out, err)

        args = ["--scheme"]
        return_value = script.run_script(args, ew, err)

        self.assertEqual("", err.getvalue())
        self.assertEqual(0, return_value)

        found = ET.fromstring(out.getvalue())
        expected = ET.parse(open("data/scheme_without_defaults.xml")).getroot()

        self.assertTrue(xml_compare(expected, found))

    def test_successful_validation(self):
        """Check that successful validation yield no text and a 0 exit value."""

        # Override abstract methods
        class NewScript(Script):
            def get_scheme(self):
                return None

            def validate_input(self, definition):
                # always succeed...
                return

            def stream_events(self, inputs, ew):
                # unused
                return

        script = NewScript()

        out = StringIO()
        err = StringIO()
        ew = EventWriter(out, err)

        args = ["--validate-arguments"]

        return_value = script.run_script(args, ew, open("data/validation.xml"))

        self.assertEqual("", err.getvalue())
        self.assertEqual("", out.getvalue())
        self.assertEqual(0, return_value)

    def test_failed_validation(self):
        """Check that failed validation writes sensible XML to stdout."""

        # Override abstract methods
        class NewScript(Script):
            def get_scheme(self):
                return None

            def validate_input(self, definition):
                raise ValueError("Big fat validation error!")

            def stream_events(self, inputs, ew):
                # unused
                return

        script = NewScript()

        out = StringIO()
        err = StringIO()
        ew = EventWriter(out, err)

        args = ["--validate-arguments"]

        return_value = script.run_script(args, ew, open("data/validation.xml"))

        expected = ET.parse(open("data/validation_error.xml")).getroot()
        found = ET.fromstring(out.getvalue())

        self.assertEqual("", err.getvalue())
        self.assertTrue(xml_compare(expected, found))
        self.assertNotEqual(0, return_value)

    def test_write_events(self):
        """Check that passing an input definition and writing a couple events goes smoothly."""

        # Override abstract methods
        class NewScript(Script):
            def get_scheme(self):
                return None

            def stream_events(self, inputs, ew):
                event = Event(
                    data="This is a test of the emergency broadcast system.",
                    stanza="fubar",
                    time="%.3f" % 1372275124.466,
                    host="localhost",
                    index="main",
                    source="hilda",
                    sourcetype="misc",
                    done=True,
                    unbroken=True
                )

                ew.write_event(event)
                ew.write_event(event)

        script = NewScript()
        input_configuration = open("data/conf_with_2_inputs.xml")

        out = StringIO()
        err = StringIO()
        ew = EventWriter(out, err)

        return_value = script.run_script([], ew, input_configuration)

        self.assertEqual(0, return_value)
        self.assertEqual("", err.getvalue())

        expected = ET.parse(open("data/stream_with_two_events.xml")).getroot()
        found = ET.fromstring(out.getvalue())

        self.assertTrue(xml_compare(expected, found))

if __name__ == "__main__":
    unittest.main()