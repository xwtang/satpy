#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Module for testing the mpop.channel module.
"""

import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest
import mock
from datetime import datetime
import numpy as np

DEFAULT_FILE_DTYPE = np.uint16
DEFAULT_FILE_SHAPE = (10, 300)
DEFAULT_FILE_DATA = np.arange(DEFAULT_FILE_SHAPE[0] * DEFAULT_FILE_SHAPE[1],
                              dtype=DEFAULT_FILE_DTYPE).reshape(DEFAULT_FILE_SHAPE)
DEFAULT_FILE_FACTORS = np.array([2.0, 1.0], dtype=np.float32)


class FakeHDF5MetaData(object):
    def __init__(self, filename, **kwargs):
        self.filename = filename

        self.d = {
            "AggregateBeginningDate": "20150101",
            "AggregateBeginningTime": "101112.5Z",
            "AggregateEndingDate": "20150102",
            "AggregateEndingTime": "111210.6Z",
            "G-Ring_Longitude": np.array([0.0, 0.1, 0.2, 0.3]),
            "G-Ring_Latitude": np.array([0.0, 0.1, 0.2, 0.3]),
            "AggregateBeginningOrbitNumber": "5",
            "AggregateEndingOrbitNumber": "6",
            "Instrument_Short_Name": "VIIRS",
            "Platform_Short_Name": "NPP",
            "N_Geo_Ref": "test_geo.h5",
            "BadFactors": np.array([-999.0, -999.0, -999.0, -999.0], dtype=np.float32),
        }

        for k in ["FakeDataset"]:
            self.d[k] = DEFAULT_FILE_DATA.copy()
            self.d[k + "/shape"] = DEFAULT_FILE_SHAPE
            self.d[k + "Factors"] = DEFAULT_FILE_FACTORS.copy()
        for k in ["FakeData"]:
            self.d[k] = DEFAULT_FILE_DATA.copy()
            self.d[k + "/shape"] = DEFAULT_FILE_SHAPE
        for k in ["FakeDataFloat"]:
            self.d[k] = DEFAULT_FILE_DATA.copy().astype(np.float32)
            self.d[k + "/shape"] = DEFAULT_FILE_SHAPE

        self.d.update(kwargs)

    def __getitem__(self, item):
        return self.d[item]


class TestSDRFileReader(unittest.TestCase):
    """Test the SDRFileReader class used by the VIIRS SDR Reader.
    """
    def setUp(self):
        from mpop.readers.viirs_sdr import FileKey
        file_keys = [
            FileKey("beginning_date", "AggregateBeginningDate"),
            FileKey("beginning_time", "AggregateBeginningTime"),
            FileKey("ending_date", "AggregateEndingDate"),
            FileKey("ending_time", "AggregateEndingTime"),
            FileKey("gring_longitude", "G-Ring_Longitude"),
            FileKey("gring_latitude", "G-Ring_Latitude"),
            FileKey("beginning_orbit_number", "AggregateBeginningOrbitNumber"),
            FileKey("ending_orbit_number", "AggregateEndingOrbitNumber"),
            FileKey("instrument_short_name", "Instrument_Short_Name"),
            FileKey("platform_short_name", "Platform_Short_Name"),
            FileKey("geo_file_reference", "N_Geo_Ref"),
            FileKey("radiance", "FakeDataset", scaling_factors="radiance_factors", units="W m-2 sr-1"),
            FileKey("radiance_factors", "FakeDatasetFactors"),
            FileKey("reflectance", "FakeDataset", scaling_factors="reflectance_factors", units="%"),
            FileKey("reflectance_factors", "FakeDatasetFactors"),
            FileKey("brightness_temperature", "FakeDataset", scaling_factors="bt_factors", units="K"),
            FileKey("bt_factors", "FakeDatasetFactors"),
            FileKey("unknown_data", "FakeData", scaling_factors="bad_factors"),
            FileKey("unknown_data2", "FakeData", file_units="fake", dtype="int64"),
            FileKey("unknown_data3", "FakeDataFloat", scaling_factors="nonexistent"),
            FileKey("bad_factors", "BadFactors"),
            FileKey("longitude", "FakeData"),
            FileKey("latitude", "FakeData"),
        ]
        self.file_keys = dict((x.name, x) for x in file_keys)

    def test_init_basic(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            self.assertEqual(file_reader.start_time, datetime(2015, 1, 1, 10, 11, 12, 500000))
            self.assertEqual(file_reader.end_time, datetime(2015, 1, 2, 11, 12, 10, 600000))
            self.assertRaises(ValueError, file_reader._parse_npp_datetime, "19580102", "120000.0Z")

    def test_get_funcs(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            gring_lon, gring_lat = file_reader.get_ring_lonlats()
            begin_orbit = file_reader.get_begin_orbit_number()
            self.assertIsInstance(begin_orbit, int)
            self.assertEqual(begin_orbit, 5)
            end_orbit = file_reader.get_end_orbit_number()
            self.assertIsInstance(end_orbit, int)
            self.assertEqual(end_orbit, 6)
            instrument_name = file_reader.get_sensor_name()
            self.assertEqual(instrument_name, "VIIRS")
            platform_name = file_reader.get_platform_name()
            self.assertEqual(platform_name, "NPP")
            geo_ref = file_reader.get_geofilename()

    def test_data_shape(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            self.assertEquals(file_reader["reflectance/shape"], (10, 300))

    def test_file_units(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            file_units = file_reader.get_file_units("reflectance")
            self.assertEqual(file_units, "1")
            file_units = file_reader.get_file_units("radiance")
            self.assertEqual(file_units, "W cm-2 sr-1")
            file_units = file_reader.get_file_units("brightness_temperature")
            self.assertEqual(file_units, "K")
            file_units = file_reader.get_file_units("unknown_data")
            self.assertIs(file_units, None)
            file_units = file_reader.get_file_units("unknown_data2")
            self.assertIs(file_units, "fake")
            file_units = file_reader.get_file_units("longitude")
            self.assertEqual(file_units, "degrees")
            file_units = file_reader.get_file_units("latitude")
            self.assertEqual(file_units, "degrees")

    def test_units(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            units = file_reader.get_units("reflectance")
            self.assertEqual(units, "%")
            units = file_reader.get_units("radiance")
            self.assertEqual(units, "W m-2 sr-1")
            units = file_reader.get_units("brightness_temperature")
            self.assertEqual(units, "K")
            units = file_reader.get_units("unknown_data")
            self.assertIs(units, None)
            units = file_reader.get_units("unknown_data2")
            self.assertIs(units, "fake")
            units = file_reader.get_units("longitude")
            self.assertEqual(units, "degrees")
            units = file_reader.get_units("latitude")
            self.assertEqual(units, "degrees")

    def test_getting_raw_data(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            for k in ["radiance", "reflectance", "brightness_temperature",
                      "longitude", "latitude", "unknown_data", "unknown_data2"]:
                data = file_reader[k]
                self.assertTrue(data.dtype == DEFAULT_FILE_DTYPE)
                np.testing.assert_array_equal(data, DEFAULT_FILE_DATA)

            for k in ["unknown_data3"]:
                data = file_reader[k]
                self.assertTrue(data.dtype == np.float32)
                np.testing.assert_array_equal(data, DEFAULT_FILE_DATA)

    def test_getting_swath_data(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            valid_data = DEFAULT_FILE_DATA * DEFAULT_FILE_FACTORS[0] + DEFAULT_FILE_FACTORS[1]
            for k in ["radiance", "reflectance", "brightness_temperature"]:
                data, mask = file_reader.get_swath_data(k)
                self.assertTrue(data.dtype == np.float32)
                self.assertTrue(mask.dtype == np.bool)
                if k == "radiance":
                    np.testing.assert_array_equal(data, valid_data * 10000.0)
                elif k == "reflectance":
                    np.testing.assert_array_equal(data, valid_data * 100.0)
                else:
                    np.testing.assert_array_equal(data, valid_data)
            for k in ["longitude", "latitude", "unknown_data"]:
                # these shouldn't have any change to their file data
                # normally unknown_data would, but the scaling factors are bad in this test file
                data, mask = file_reader.get_swath_data(k)
                self.assertTrue(data.dtype == np.float32)
                self.assertTrue(mask.dtype == np.bool)
                np.testing.assert_array_equal(data, DEFAULT_FILE_DATA)
                if k == "unknown_data":
                    # bad fill values should result in bad science data
                    np.testing.assert_array_equal(mask, True)
            for k in ["unknown_data2"]:
                data, mask = file_reader.get_swath_data(k)
                self.assertTrue(data.dtype == np.int64)
                self.assertTrue(mask.dtype == np.bool)
                np.testing.assert_array_equal(data, DEFAULT_FILE_DATA)
            for k in ["unknown_data3"]:
                data, mask = file_reader.get_swath_data(k)
                self.assertTrue(data.dtype == np.float32)
                self.assertTrue(mask.dtype == np.bool)
                np.testing.assert_array_equal(data, DEFAULT_FILE_DATA)

    def test_getting_swath_data_inplace(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            data_out = np.zeros(DEFAULT_FILE_SHAPE, dtype=np.float32)
            mask_out = np.zeros(DEFAULT_FILE_SHAPE, dtype=np.bool)
            for k in ["radiance", "reflectance", "brightness_temperature",
                      "longitude", "latitude", "unknown_data"]:
                data, mask = file_reader.get_swath_data(k, data_out=data_out, mask_out=mask_out)
                self.assertTrue(len(np.nonzero(data != 0)[0]) > 0)
                self.assertTrue(data.dtype == np.float32)
                self.assertTrue(mask.dtype == np.bool)
                data_out[:] = 0
                mask_out[:] = False

            data_out = np.zeros(DEFAULT_FILE_SHAPE, dtype=np.int64)
            for k in ["unknown_data2"]:
                data, mask = file_reader.get_swath_data(k, data_out=data_out, mask_out=mask_out)
                self.assertTrue(len(np.nonzero(data != 0)[0]) > 0)
                self.assertTrue(data.dtype == np.int64)
                self.assertTrue(mask.dtype == np.bool)
                data_out[:] = 0
                mask_out[:] = False

    def test_getting_swath_data_disk(self):
        from mpop.readers.viirs_sdr import SDRFileReader
        patcher = mock.patch.object(SDRFileReader, '__bases__', (FakeHDF5MetaData,))
        with patcher:
            patcher.is_local = True
            file_reader = SDRFileReader("fake_file_type", "test.h5", file_keys=self.file_keys)
            self.assertRaises(NotImplementedError, file_reader.get_swath_data, "radiance", filename="test.dat")


class OldTestViirsSDRReader(object):
    """Class for testing the VIIRS SDR reader class.
    """
    
    def test_get_swath_segment(self):
        """
        Test choosing swath segments based on datatime interval
        """
        
        filenames = [
            "SVM15_npp_d20130312_t1034305_e1035546_b07108_c20130312110058559507_cspp_dev.h5", 
            "SVM15_npp_d20130312_t1035559_e1037201_b07108_c20130312110449303310_cspp_dev.h5",
            "SVM15_npp_d20130312_t1037213_e1038455_b07108_c20130312110755391459_cspp_dev.h5",
            "SVM15_npp_d20130312_t1038467_e1040109_b07108_c20130312111106961103_cspp_dev.h5",
            "SVM15_npp_d20130312_t1040121_e1041363_b07108_c20130312111425464510_cspp_dev.h5",
            "SVM15_npp_d20130312_t1041375_e1043017_b07108_c20130312111720550253_cspp_dev.h5",
            "SVM15_npp_d20130312_t1043029_e1044271_b07108_c20130312112246726129_cspp_dev.h5",
            "SVM15_npp_d20130312_t1044283_e1045525_b07108_c20130312113037160389_cspp_dev.h5",
            "SVM15_npp_d20130312_t1045537_e1047179_b07108_c20130312114330237590_cspp_dev.h5",
            "SVM15_npp_d20130312_t1047191_e1048433_b07108_c20130312120148075096_cspp_dev.h5",
            "SVM15_npp_d20130312_t1048445_e1050070_b07108_c20130312120745231147_cspp_dev.h5",
            ]
       

        #
        # Test search for multiple granules
        result = [
            "SVM15_npp_d20130312_t1038467_e1040109_b07108_c20130312111106961103_cspp_dev.h5",
            "SVM15_npp_d20130312_t1040121_e1041363_b07108_c20130312111425464510_cspp_dev.h5",
            "SVM15_npp_d20130312_t1041375_e1043017_b07108_c20130312111720550253_cspp_dev.h5",
            "SVM15_npp_d20130312_t1043029_e1044271_b07108_c20130312112246726129_cspp_dev.h5",
            "SVM15_npp_d20130312_t1044283_e1045525_b07108_c20130312113037160389_cspp_dev.h5",
            ]

        tstart = datetime(2013, 3, 12, 10, 39)
        tend = datetime(2013, 3, 12, 10, 45)

        

        sublist = _get_swathsegment(filenames, tstart, tend)

        self.assert_(sublist == result)


        #
        # Test search for single granule
        tslot = datetime(2013, 3, 12, 10, 45)

        result_file = [
            "SVM15_npp_d20130312_t1044283_e1045525_b07108_c20130312113037160389_cspp_dev.h5",
            ]
        
        single_file = _get_swathsegment(filenames, tslot)

        self.assert_(result_file == single_file)


def suite():
    """The test suite for test_viirs_sdr.
    """
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()
    mysuite.addTest(loader.loadTestsFromTestCase(TestSDRFileReader))
    
    return mysuite
