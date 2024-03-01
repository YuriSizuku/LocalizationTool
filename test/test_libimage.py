import time
import logging
import unittest
import numpy as np

from common import *
import libimage

class TestIndexPattern(unittest.TestCase):
    def test_example_siwzzle1(self):
        res = libimage.make_swizzle_pattern(3)
        self.assertEqual(res.shape, (8, 8))
        self.assertEqual(res[-1, -1], 63)
        
    def test_example_tile1(self):
        res = libimage.make_tile_pattern(4, 2, 3, 2)
        self.assertEqual(res.shape, (4, 8))
        self.assertEqual(res[3, 3], 23)
        self.assertEqual(res[-1, -1], -1)
        
    def test_linearpalatte(self):
        pass

class TestTileImage(unittest.TestCase):
    def test_file_it(self):
        with open(paths_bin["it"], 'rb') as fp:
            data = np.frombuffer(fp.read(), dtype=np.uint8)
       
        palatte = np.array([
            [0xFF, 0xFF, 0xFF, 0],
            [0xFF, 0xFF, 0xFF, 0x3F],
            [0xFF, 0xFF, 0xFF, 0x8F],
            [0xFF, 0xFF, 0xFF, 0xFF]
        ], dtype=np.uint8)
        n_tile = 3561
        tile_info = (18, 20, 2, (20*18)//4+2)
        datasize = n_tile*tile_info[3]
        
        # test encode decode without palatte
        img = libimage.decode_tile_image(data, tile_info=tile_info, n_tile=n_tile)
        data2 =libimage.enocde_tile_image(img, tile_info=tile_info, n_tile=n_tile)
        self.assertTrue(np.array_equal(data[:datasize], data2[:datasize]))

        # test encode decode with palatte
        start = time.time()
        img = libimage.decode_tile_image(data, tile_info=tile_info, palatte=palatte, n_tile=n_tile)
        print(f"{(time.time()-start)*1000: .4f} ms for decode_tile_img with {tile_info} (with palatte)")
        # Image.fromarray(img).save("project/pyexe_libtext/build/it.png")
        start = time.time()
        data2 =libimage.enocde_tile_image(img, tile_info=tile_info, palatte=palatte, n_tile=n_tile)
        print(f"{(time.time()-start)*1000: .4f} ms for enocde_tile_img with {tile_info} (with palatte)")
        self.assertTrue(np.array_equal(data[:datasize], data2[:datasize]))

class TestPalatteImage(unittest.TestCase):
    def test_example_index4(self):
        palatte = libimage.make_linear_palatte(4)
        img1 = np.zeros([10, 10, 4], dtype=np.uint8)
        # img1[..., 3] = np.random.randint(0, 16, (10,), dtype=np.uint8)
        for y in range(img1.shape[0]):
            for x in range(img1.shape[1]):
                img1[y][x][3] = (y + x) % 16
        
        img2 = libimage.decode_palatte(img1, palatte)
        palatte2 = libimage.quantize_palatte(img2, 4)
        self.assertTrue(np.array_equal(palatte, palatte2))
        img3 = libimage.encode_palatte(img2, palatte)
        self.assertEqual(img1.shape,  img3.shape)
        self.assertTrue(np.array_equal(img1[..., 3], img3[..., 3]))

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(funcName)s: %(message)s")
    unittest.main()