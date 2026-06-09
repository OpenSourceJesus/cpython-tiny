"""zipimport provides support for importing Python modules from Zip archives.

This module exports two objects:
- zipimporter: a class; its constructor takes a path to a Zip archive.
- ZipImportError: exception raised by zipimporter objects. It's a
  subclass of ImportError, so it can be caught as ImportError, too.

It is usually not needed to use the zipimport module explicitly; it is
used by the builtin import mechanism for sys.path items that are paths
to Zip archives.
"""

import _frozen_importlib_external as _bootstrap_external
from _frozen_importlib_external import _unpack_uint16, _unpack_uint32, _unpack_uint64
import _frozen_importlib as _bootstrap                        
import _imp                             
import _io            
import marshal             
import time              

__all__ = ['ZipImportError', 'zipimporter']


path_sep = _bootstrap_external.path_sep
alt_path_sep = _bootstrap_external.path_separators[1:]


class ZipImportError(ImportError):
    pass

                         
_zip_directory_cache = {}

END_CENTRAL_DIR_SIZE = 22
END_CENTRAL_DIR_SIZE_64 = 56
END_CENTRAL_DIR_LOCATOR_SIZE_64 = 20
STRING_END_ARCHIVE = b'PK\x05\x06'                           
STRING_END_LOCATOR_64 = b'PK\x06\x07'                                
STRING_END_ZIP_64 = b'PK\x06\x06'                        
MAX_COMMENT_LEN = (1 << 16) - 1
MAX_UINT32 = 0xffffffff
ZIP64_EXTRA_TAG = 0x1

class zipimporter(_bootstrap_external._LoaderBasics):
    """zipimporter(archivepath) -> zipimporter object

    Create a new zipimporter instance. 'archivepath' must be a path to
    a zipfile, or to a specific path inside a zipfile. For example, it can be
    '/tmp/myimport.zip', or '/tmp/myimport.zip/mydirectory', if mydirectory is a
    valid directory inside the archive.

    'ZipImportError is raised if 'archivepath' doesn't point to a valid Zip
    archive.

    The 'archive' attribute of zipimporter objects contains the name of the
    zipfile targeted.
    """

                                                                           
                                                                           
                                                 
    def __init__(self, path):
        if not isinstance(path, str):
            raise TypeError(f"expected str, not {type(path)!r}")
        if not path:
            raise ZipImportError('archive path is empty', path=path)
        if alt_path_sep:
            path = path.replace(alt_path_sep, path_sep)

        prefix = []
        while True:
            try:
                st = _bootstrap_external._path_stat(path)
            except (OSError, ValueError):
                                                                       
                                           
                dirname, basename = _bootstrap_external._path_split(path)
                if dirname == path:
                    raise ZipImportError('not a Zip file', path=path)
                path = dirname
                prefix.append(basename)
            else:
                           
                if (st.st_mode & 0o170000) != 0o100000:                
                                     
                    raise ZipImportError('not a Zip file', path=path)
                break

        if path not in _zip_directory_cache:
            _zip_directory_cache[path] = _read_directory(path)
        self.archive = path
                                                         
        self.prefix = _bootstrap_external._path_join(*prefix[::-1])
        if self.prefix:
            self.prefix += path_sep


    def find_spec(self, fullname, target=None):
        """Create a ModuleSpec for the specified module.

        Returns None if the module cannot be found.
        """
        module_info = _get_module_info(self, fullname)
        if module_info is not None:
            return _bootstrap.spec_from_loader(fullname, self, is_package=module_info)
        else:
                                                                              
                                                                  

                                                                          
                                                             
            modpath = _get_module_path(self, fullname)
            if _is_dir(self, modpath):
                                                           
                                                                   
                                               
                path = f'{self.archive}{path_sep}{modpath}'
                spec = _bootstrap.ModuleSpec(name=fullname, loader=None,
                                             is_package=True)
                spec.submodule_search_locations.append(path)
                return spec
            else:
                return None

    def get_code(self, fullname):
        """get_code(fullname) -> code object.

        Return the code object for the specified module. Raise ZipImportError
        if the module couldn't be imported.
        """
        code, ispackage, modpath = _get_module_code(self, fullname)
        return code


    def get_data(self, pathname):
        """get_data(pathname) -> string with file data.

        Return the data associated with 'pathname'. Raise OSError if
        the file wasn't found.
        """
        if alt_path_sep:
            pathname = pathname.replace(alt_path_sep, path_sep)

        key = pathname
        if pathname.startswith(self.archive + path_sep):
            key = pathname[len(self.archive + path_sep):]

        try:
            toc_entry = self._get_files()[key]
        except KeyError:
            raise OSError(0, '', key)
        if toc_entry is None:
            return b''
        return _get_data(self.archive, toc_entry)


                                                            
    def get_filename(self, fullname):
        """get_filename(fullname) -> filename string.

        Return the filename for the specified module or raise ZipImportError
        if it couldn't be imported.
        """
                                                                   
                                                           
        code, ispackage, modpath = _get_module_code(self, fullname)
        return modpath


    def get_source(self, fullname):
        """get_source(fullname) -> source string.

        Return the source code for the specified module. Raise ZipImportError
        if the module couldn't be found, return None if the archive does
        contain the module, but has no source for it.
        """
        mi = _get_module_info(self, fullname)
        if mi is None:
            raise ZipImportError(f"can't find module {fullname!r}", name=fullname)

        path = _get_module_path(self, fullname)
        if mi:
            fullpath = _bootstrap_external._path_join(path, '__init__.py')
        else:
            fullpath = f'{path}.py'

        try:
            toc_entry = self._get_files()[fullpath]
        except KeyError:
                                               
            return None
        return _get_data(self.archive, toc_entry).decode()


                                                                      
    def is_package(self, fullname):
        """is_package(fullname) -> bool.

        Return True if the module specified by fullname is a package.
        Raise ZipImportError if the module couldn't be found.
        """
        mi = _get_module_info(self, fullname)
        if mi is None:
            raise ZipImportError(f"can't find module {fullname!r}", name=fullname)
        return mi


    def get_resource_reader(self, fullname):
        """Return the ResourceReader for a module in a zip file."""
        from importlib.readers import ZipReader

        return ZipReader(self, fullname)


    def _get_files(self):
        """Return the files within the archive path."""
        try:
            files = _zip_directory_cache[self.archive]
        except KeyError:
            try:
                files = _zip_directory_cache[self.archive] = _read_directory(self.archive)
            except ZipImportError:
                files = {}

        return files


    def invalidate_caches(self):
        """Invalidates the cache of file data of the archive path."""
        _zip_directory_cache.pop(self.archive, None)


    def __repr__(self):
        return f'<zipimporter object "{self.archive}{path_sep}{self.prefix}">'


                                                                
                                                           
                                                     
                                                                   
                                    
_zip_searchorder = (
    (path_sep + '__init__.pyc', True, True),
    (path_sep + '__init__.py', False, True),
    ('.pyc', True, False),
    ('.py', False, False),
)

                                                            
                              
def _get_module_path(self, fullname):
    return self.prefix + fullname.rpartition('.')[2]

                                       
def _is_dir(self, path):
                                                                   
                                                                    
                                      
    dirpath = path + path_sep
                                                                      
    return dirpath in self._get_files()

                                         
def _get_module_info(self, fullname):
    path = _get_module_path(self, fullname)
    for suffix, isbytecode, ispackage in _zip_searchorder:
        fullpath = path + suffix
        if fullpath in self._get_files():
            return ispackage
    return None


                

                                                        
 
                                                                 
                                                                  
 
                         
 
                                                                         
                                                        
                                                          
                                                     
                                               
                                                                 
                                                      
                                                      
                                              
   
 
                                                                     
                                  
def _read_directory(archive):
    try:
        fp = _io.open_code(archive)
    except OSError:
        raise ZipImportError(f"can't open Zip file: {archive!r}", path=archive)

    with fp:
                                                                              
                                                                                 
                                                                                
        start_offset = fp.tell()
        try:
                                         
            try:
                fp.seek(0, 2)
                file_size = fp.tell()
            except OSError:
                raise ZipImportError(f"can't read Zip file: {archive!r}",
                                     path=archive)
            max_comment_plus_dirs_size = (
                MAX_COMMENT_LEN + END_CENTRAL_DIR_SIZE +
                END_CENTRAL_DIR_SIZE_64 + END_CENTRAL_DIR_LOCATOR_SIZE_64)
            max_comment_start = max(file_size - max_comment_plus_dirs_size, 0)
            try:
                fp.seek(max_comment_start)
                data = fp.read(max_comment_plus_dirs_size)
            except OSError:
                raise ZipImportError(f"can't read Zip file: {archive!r}",
                                     path=archive)
            pos = data.rfind(STRING_END_ARCHIVE)
            pos64 = data.rfind(STRING_END_ZIP_64)

            if (pos64 >= 0 and pos64+END_CENTRAL_DIR_SIZE_64+END_CENTRAL_DIR_LOCATOR_SIZE_64==pos):
                                                              
                buffer = data[pos64:pos64 + END_CENTRAL_DIR_SIZE_64]
                if len(buffer) != END_CENTRAL_DIR_SIZE_64:
                    raise ZipImportError(
                        f"corrupt Zip64 file: Expected {END_CENTRAL_DIR_SIZE_64} byte "
                        f"zip64 central directory, but read {len(buffer)} bytes.",
                        path=archive)
                header_position = file_size - len(data) + pos64

                central_directory_size = _unpack_uint64(buffer[40:48])
                central_directory_position = _unpack_uint64(buffer[48:56])
                num_entries = _unpack_uint64(buffer[24:32])
            elif pos >= 0:
                buffer = data[pos:pos+END_CENTRAL_DIR_SIZE]
                if len(buffer) != END_CENTRAL_DIR_SIZE:
                    raise ZipImportError(f"corrupt Zip file: {archive!r}",
                                         path=archive)

                header_position = file_size - len(data) + pos

                                                                                 
                                          
                central_directory_size = _unpack_uint32(buffer[12:16])
                central_directory_position = _unpack_uint32(buffer[16:20])
                num_entries = _unpack_uint16(buffer[8:10])

                                                                                   
                                                                    
            else:
                raise ZipImportError(f'not a Zip file: {archive!r}',
                                     path=archive)

                                                                             
                                      
                                                                                  
                                                                              
            if header_position < central_directory_size:
                raise ZipImportError(f'bad central directory size: {archive!r}', path=archive)
            if header_position < central_directory_position:
                raise ZipImportError(f'bad central directory offset: {archive!r}', path=archive)
            header_position -= central_directory_size
                                                                                    
                                                                                   
                                                                           
            arc_offset = header_position - central_directory_position
            if arc_offset < 0:
                raise ZipImportError(f'bad central directory size or offset: {archive!r}', path=archive)

            files = {}
                                        
            count = 0
            try:
                fp.seek(header_position)
            except OSError:
                raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
            while True:
                buffer = fp.read(46)
                if len(buffer) < 4:
                    raise EOFError('EOF read where not expected')
                                      
                if buffer[:4] != b'PK\x01\x02':
                    if count != num_entries:
                        raise ZipImportError(
                            f"mismatched num_entries: {count} should be {num_entries} in {archive!r}",
                            path=archive,
                        )
                    break                                                              
                if len(buffer) != 46:
                    raise EOFError('EOF read where not expected')
                flags = _unpack_uint16(buffer[8:10])
                compress = _unpack_uint16(buffer[10:12])
                time = _unpack_uint16(buffer[12:14])
                date = _unpack_uint16(buffer[14:16])
                crc = _unpack_uint32(buffer[16:20])
                data_size = _unpack_uint32(buffer[20:24])
                file_size = _unpack_uint32(buffer[24:28])
                name_size = _unpack_uint16(buffer[28:30])
                extra_size = _unpack_uint16(buffer[30:32])
                comment_size = _unpack_uint16(buffer[32:34])
                file_offset = _unpack_uint32(buffer[42:46])
                header_size = name_size + extra_size + comment_size

                try:
                    name = fp.read(name_size)
                except OSError:
                    raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
                if len(name) != name_size:
                    raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
                                                                                   
                                                                            
                                                       
                try:
                    extra_data_len = header_size - name_size
                    extra_data = memoryview(fp.read(extra_data_len))

                    if len(extra_data) != extra_data_len:
                        raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
                except OSError:
                    raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)

                if flags & 0x800:
                                                
                    name = name.decode()
                else:
                                                      
                    try:
                        name = name.decode('ascii')
                    except UnicodeDecodeError:
                        name = name.decode('latin1').translate(cp437_table)

                name = name.replace('/', path_sep)
                path = _bootstrap_external._path_join(archive, name)

                                                   
                if (
                    file_size == MAX_UINT32 or
                    data_size == MAX_UINT32 or
                    file_offset == MAX_UINT32
                ):
                                                                                          
                                 
                    while extra_data:
                        if len(extra_data) < 4:
                            raise ZipImportError(f"can't read header extra: {archive!r}", path=archive)
                        tag = _unpack_uint16(extra_data[:2])
                        size = _unpack_uint16(extra_data[2:4])
                        if len(extra_data) < 4 + size:
                            raise ZipImportError(f"can't read header extra: {archive!r}", path=archive)
                        if tag == ZIP64_EXTRA_TAG:
                            if (len(extra_data) - 4) % 8 != 0:
                                raise ZipImportError(f"can't read header extra: {archive!r}", path=archive)
                            num_extra_values = (len(extra_data) - 4) // 8
                            if num_extra_values > 3:
                                raise ZipImportError(f"can't read header extra: {archive!r}", path=archive)
                            import struct
                            values = list(struct.unpack_from(f"<{min(num_extra_values, 3)}Q",
                                                             extra_data, offset=4))

                                                                                           
                                                                                           
                                                                              
                            if file_size == MAX_UINT32:
                                file_size = values.pop(0)
                            if data_size == MAX_UINT32:
                                data_size = values.pop(0)
                            if file_offset == MAX_UINT32:
                                file_offset = values.pop(0)

                            break

                                                                                          
                                                                   
                        extra_data = extra_data[4+size:]
                    else:
                        _bootstrap._verbose_message(
                            "zipimport: suspected zip64 but no zip64 extra for {!r}",
                            path,
                        )
                                                                                            
                                                                                            
                                                                      
                                                                                          
                                       
                if file_offset > central_directory_position:
                    raise ZipImportError(f'bad local header offset: {archive!r}', path=archive)
                file_offset += arc_offset

                t = (path, compress, data_size, file_size, file_offset, time, date, crc)
                files[name] = t
                count += 1
        finally:
            fp.seek(start_offset)
    _bootstrap._verbose_message('zipimport: found {} names in {!r}', count, archive)

                               
    count = 0
    for name in list(files):
        while True:
            i = name.rstrip(path_sep).rfind(path_sep)
            if i < 0:
                break
            name = name[:i + 1]
            if name in files:
                break
            files[name] = None
            count += 1
    if count:
        _bootstrap._verbose_message('zipimport: added {} implicit directories in {!r}',
                                    count, archive)
    return files

                                                     
                                                                
                                     
 
                                                                 
                     
cp437_table = (
                                   
    '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f'
    '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
    ' !"#$%&\'()*+,-./'
    '0123456789:;<=>?'
    '@ABCDEFGHIJKLMNO'
    'PQRSTUVWXYZ[\\]^_'
    '`abcdefghijklmno'
    'pqrstuvwxyz{|}~\x7f'
                                       
    '\xc7\xfc\xe9\xe2\xe4\xe0\xe5\xe7'
    '\xea\xeb\xe8\xef\xee\xec\xc4\xc5'
    '\xc9\xe6\xc6\xf4\xf6\xf2\xfb\xf9'
    '\xff\xd6\xdc\xa2\xa3\xa5\u20a7\u0192'
    '\xe1\xed\xf3\xfa\xf1\xd1\xaa\xba'
    '\xbf\u2310\xac\xbd\xbc\xa1\xab\xbb'
    '\u2591\u2592\u2593\u2502\u2524\u2561\u2562\u2556'
    '\u2555\u2563\u2551\u2557\u255d\u255c\u255b\u2510'
    '\u2514\u2534\u252c\u251c\u2500\u253c\u255e\u255f'
    '\u255a\u2554\u2569\u2566\u2560\u2550\u256c\u2567'
    '\u2568\u2564\u2565\u2559\u2558\u2552\u2553\u256b'
    '\u256a\u2518\u250c\u2588\u2584\u258c\u2590\u2580'
    '\u03b1\xdf\u0393\u03c0\u03a3\u03c3\xb5\u03c4'
    '\u03a6\u0398\u03a9\u03b4\u221e\u03c6\u03b5\u2229'
    '\u2261\xb1\u2265\u2264\u2320\u2321\xf7\u2248'
    '\xb0\u2219\xb7\u221a\u207f\xb2\u25a0\xa0'
)

_importing_zlib = False
_zlib_decompress = None

                                                                      
                                                                     
                          
def _get_zlib_decompress_func():
    global _zlib_decompress
    if _zlib_decompress:
        return _zlib_decompress

    global _importing_zlib
    if _importing_zlib:
                                                     
                                       
        _bootstrap._verbose_message('zipimport: zlib UNAVAILABLE')
        raise ZipImportError("can't decompress data; zlib not available")

    _importing_zlib = True
    try:
        from zlib import decompress as _zlib_decompress
    except Exception:
        _bootstrap._verbose_message('zipimport: zlib UNAVAILABLE')
        raise ZipImportError("can't decompress data; zlib not available")
    finally:
        _importing_zlib = False

    _bootstrap._verbose_message('zipimport: zlib available')
    return _zlib_decompress


_importing_zstd = False
_zstd_decompressor_class = None

                                                                              
                                               
def _get_zstd_decompressor_class():
    global _zstd_decompressor_class
    if _zstd_decompressor_class:
        return _zstd_decompressor_class

    global _importing_zstd
    if _importing_zstd:
                                                      
                                       
        _bootstrap._verbose_message("zipimport: zstd UNAVAILABLE")
        raise ZipImportError("can't decompress data; zstd not available")

    _importing_zstd = True
    try:
        from _zstd import ZstdDecompressor as _zstd_decompressor_class
    except Exception:
        _bootstrap._verbose_message("zipimport: zstd UNAVAILABLE")
        raise ZipImportError("can't decompress data; zstd not available")
    finally:
        _importing_zstd = False

    _bootstrap._verbose_message("zipimport: zstd available")
    return _zstd_decompressor_class


def _zstd_decompress(data):
                                                                           
                                                                
    results = []
    while True:
        decomp = _get_zstd_decompressor_class()()
        results.append(decomp.decompress(data))
        if not decomp.eof:
            raise ZipImportError("zipimport: zstd compressed data ended before "
                                 "the end-of-stream marker")
        data = decomp.unused_data
        if not data:
            break
    return b"".join(results)


                                                                             
def _get_data(archive, toc_entry):
    datapath, compress, data_size, file_size, file_offset, time, date, crc = toc_entry
    if data_size < 0:
        raise ZipImportError('negative data size')

    with _io.open_code(archive) as fp:
                                                             
        try:
            fp.seek(file_offset)
        except OSError:
            raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
        buffer = fp.read(30)
        if len(buffer) != 30:
            raise EOFError('EOF read where not expected')

        if buffer[:4] != b'PK\x03\x04':
                                    
            raise ZipImportError(f'bad local file header: {archive!r}', path=archive)

        name_size = _unpack_uint16(buffer[26:28])
        extra_size = _unpack_uint16(buffer[28:30])
        header_size = 30 + name_size + extra_size
        file_offset += header_size                      
        try:
            fp.seek(file_offset)
        except OSError:
            raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
        raw_data = fp.read(data_size)
        if len(raw_data) != data_size:
            raise OSError("zipimport: can't read data")

    match compress:
        case 0:          
            return raw_data
        case 8:                    
            try:
                decompress = _get_zlib_decompress_func()
            except Exception:
                raise ZipImportError("can't decompress data; zlib not available")
            return decompress(raw_data, -15)
        case 93:        
            try:
                return _zstd_decompress(raw_data)
            except Exception:
                raise ZipImportError("could not decompress zstd data")
                                                                
        case _:
            raise ZipImportError(f"zipimport: unsupported compression {compress}")


                                                                   
                                                             
                                                
def _eq_mtime(t1, t2):
                                                     
    return abs(t1 - t2) <= 1


                                                          
                                                                          
                                                                       
def _unmarshal_code(self, pathname, fullpath, fullname, data):
    exc_details = {
        'name': fullname,
        'path': fullpath,
    }

    flags = _bootstrap_external._classify_pyc(data, fullname, exc_details)

    hash_based = flags & 0b1 != 0
    if hash_based:
        check_source = flags & 0b10 != 0
        if (_imp.check_hash_based_pycs != 'never' and
                (check_source or _imp.check_hash_based_pycs == 'always')):
            source_bytes = _get_pyc_source(self, fullpath)
            if source_bytes is not None:
                source_hash = _imp.source_hash(
                    _imp.pyc_magic_number_token,
                    source_bytes,
                )

                _bootstrap_external._validate_hash_pyc(
                    data, source_hash, fullname, exc_details)
    else:
        source_mtime, source_size = \
            _get_mtime_and_size_of_source(self, fullpath)

        if source_mtime:
                                                                      
                                                          
            if (not _eq_mtime(_unpack_uint32(data[8:12]), source_mtime) or
                    _unpack_uint32(data[12:16]) != source_size):
                _bootstrap._verbose_message(
                    f'bytecode is stale for {fullname!r}')
                return None

    code = marshal.loads(data[16:])
    if not isinstance(code, _code_type):
        raise TypeError(f'compiled module {pathname!r} is not a code object')
    return code

_code_type = type(_unmarshal_code.__code__)


                                                                   
                                                              
def _normalize_line_endings(source):
    source = source.replace(b'\r\n', b'\n')
    source = source.replace(b'\r', b'\n')
    return source

                                                                 
                           
def _compile_source(pathname, source, module):
    source = _normalize_line_endings(source)
    return compile(source, pathname, 'exec', dont_inherit=True, module=module)

                                                                  
                                                             
def _parse_dostime(d, t):
    return time.mktime((
        (d >> 9) + 1980,                      
        (d >> 5) & 0xF,                       
        d & 0x1F,                           
        t >> 11,                                
        (t >> 5) & 0x3F,                         
        (t & 0x1F) * 2,                             
        -1, -1, -1))

                                                        
                                                          
                                      
def _get_mtime_and_size_of_source(self, path):
    try:
                                        
        assert path[-1:] in ('c', 'o')
        path = path[:-1]
        toc_entry = self._get_files()[path]
                                                             
                                         
        time = toc_entry[5]
        date = toc_entry[6]
        uncompressed_size = toc_entry[3]
        return _parse_dostime(date, time), uncompressed_size
    except (KeyError, IndexError, TypeError):
        return 0, 0


                                                        
                                                         
               
def _get_pyc_source(self, path):
                                    
    assert path[-1:] in ('c', 'o')
    path = path[:-1]

    try:
        toc_entry = self._get_files()[path]
    except KeyError:
        return None
    else:
        return _get_data(self.archive, toc_entry)


                                                             
             
def _get_module_code(self, fullname):
    path = _get_module_path(self, fullname)
    import_error = None
    for suffix, isbytecode, ispackage in _zip_searchorder:
        fullpath = path + suffix
        _bootstrap._verbose_message('trying {}{}{}', self.archive, path_sep, fullpath, verbosity=2)
        try:
            toc_entry = self._get_files()[fullpath]
        except KeyError:
            pass
        else:
            modpath = toc_entry[0]
            data = _get_data(self.archive, toc_entry)
            code = None
            if isbytecode:
                try:
                    code = _unmarshal_code(self, modpath, fullpath, fullname, data)
                except ImportError as exc:
                    import_error = exc
            else:
                code = _compile_source(modpath, data, fullname)
            if code is None:
                                                        
                                        
                continue
            modpath = toc_entry[0]
            return code, ispackage, modpath
    else:
        if import_error:
            msg = f"module load failed: {import_error}"
            raise ZipImportError(msg, name=fullname) from import_error
        else:
            raise ZipImportError(f"can't find module {fullname!r}", name=fullname)
