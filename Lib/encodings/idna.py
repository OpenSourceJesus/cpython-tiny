                                                                 

import stringprep, re, codecs
from unicodedata import ucd_3_2_0 as unicodedata

                  
dots = re.compile("[\u002E\u3002\uFF0E\uFF61]")

                
ace_prefix = b"xn--"
sace_prefix = "xn--"

                                                        
def nameprep(label):                      
         
    newlabel = []
    for c in label:
        if stringprep.in_table_b1(c):
                            
            continue
        newlabel.append(stringprep.map_table_b2(c))
    label = "".join(newlabel)

               
    label = unicodedata.normalize("NFKC", label)

              
    for i, c in enumerate(label):
        if stringprep.in_table_c12(c) or \
           stringprep.in_table_c22(c) or \
           stringprep.in_table_c3(c) or \
           stringprep.in_table_c4(c) or \
           stringprep.in_table_c5(c) or \
           stringprep.in_table_c6(c) or \
           stringprep.in_table_c7(c) or \
           stringprep.in_table_c8(c) or \
           stringprep.in_table_c9(c):
            raise UnicodeEncodeError("idna", label, i, i+1, f"Invalid character {c!r}")

                
    RandAL = [stringprep.in_table_d1(x) for x in label]
    if any(RandAL):
                                                                    
                
                                                              
                                                      
                                                                     
                                              
        for i, x in enumerate(label):
            if stringprep.in_table_d2(x):
                raise UnicodeEncodeError("idna", label, i, i+1,
                                         "Violation of BIDI requirement 2")
                                                            
                                                                
                                                            
                                  
        if not RandAL[0]:
            raise UnicodeEncodeError("idna", label, 0, 1,
                                     "Violation of BIDI requirement 3")
        if not RandAL[-1]:
            raise UnicodeEncodeError("idna", label, len(label)-1, len(label),
                                     "Violation of BIDI requirement 3")

    return label

def ToASCII(label):                        
    try:
                           
        label_ascii = label.encode("ascii")
    except UnicodeEncodeError:
        pass
    else:
                                                        
                         
        if 0 < len(label_ascii) < 64:
            return label_ascii
        if len(label) == 0:
            raise UnicodeEncodeError("idna", label, 0, 1, "label empty")
        else:
            raise UnicodeEncodeError("idna", label, 0, len(label), "label too long")

                      
    label = nameprep(label)

                                        
                       
    try:
        label_ascii = label.encode("ascii")
    except UnicodeEncodeError:
        pass
    else:
                         
        if 0 < len(label) < 64:
            return label_ascii
        if len(label) == 0:
            raise UnicodeEncodeError("idna", label, 0, 1, "label empty")
        else:
            raise UnicodeEncodeError("idna", label, 0, len(label), "label too long")

                              
    if label.lower().startswith(sace_prefix):
        raise UnicodeEncodeError(
            "idna", label, 0, len(sace_prefix), "Label starts with ACE prefix")

                                  
    label_ascii = label.encode("punycode")

                                
    label_ascii = ace_prefix + label_ascii

                        
                                                      
    if len(label_ascii) < 64:
        return label_ascii
    raise UnicodeEncodeError("idna", label, 0, len(label), "label too long")

def ToUnicode(label):
    if len(label) > 1024:
                                                                         
                                                                 
                                                                          
                                    
                                                                            
                                                                            
                                                                           
                                                      
        if isinstance(label, str):
            label = label.encode("utf-8", errors="backslashreplace")
        raise UnicodeDecodeError("idna", label, 0, len(label), "label way too long")
                             
    if isinstance(label, bytes):
        pure_ascii = True
    else:
        try:
            label = label.encode("ascii")
            pure_ascii = True
        except UnicodeEncodeError:
            pure_ascii = False
    if not pure_ascii:
        assert isinstance(label, str)
                                  
        label = nameprep(label)
                                                                     
        try:
            label = label.encode("ascii")
        except UnicodeEncodeError as exc:
            raise UnicodeEncodeError("idna", label, exc.start, exc.end,
                                     "Invalid character in IDN label")
                                  
    assert isinstance(label, bytes)
    if not label.lower().startswith(ace_prefix):
        return str(label, "ascii")

                               
    label1 = label[len(ace_prefix):]

                                   
    try:
        result = label1.decode("punycode")
    except UnicodeDecodeError as exc:
        offset = len(ace_prefix)
        raise UnicodeDecodeError("idna", label, offset+exc.start, offset+exc.end, exc.reason)

                           
    label2 = ToASCII(result)

                                                                 
                                           
    if str(label, "ascii").lower() != str(label2, "ascii"):
        raise UnicodeDecodeError("idna", label, 0, len(label),
                                 f"IDNA does not round-trip, '{label!r}' != '{label2!r}'")

                                         
    return result

              

class Codec(codecs.Codec):
    def encode(self, input, errors='strict'):

        if errors != 'strict':
                                                                     
            raise UnicodeError(f"Unsupported error handling: {errors}")

        if not input:
            return b'', 0

        try:
            result = input.encode('ascii')
        except UnicodeEncodeError:
            pass
        else:
                                   
            labels = result.split(b'.')
            for i, label in enumerate(labels[:-1]):
                if len(label) == 0:
                    offset = sum(len(l) for l in labels[:i]) + i
                    raise UnicodeEncodeError("idna", input, offset, offset+1,
                                             "label empty")
            for i, label in enumerate(labels):
                if len(label) >= 64:
                    offset = sum(len(l) for l in labels[:i]) + i
                    raise UnicodeEncodeError("idna", input, offset, offset+len(label),
                                             "label too long")
            return result, len(input)

        result = bytearray()
        labels = dots.split(input)
        if labels and not labels[-1]:
            trailing_dot = b'.'
            del labels[-1]
        else:
            trailing_dot = b''
        for i, label in enumerate(labels):
            if result:
                                  
                result.extend(b'.')
            try:
                result.extend(ToASCII(label))
            except (UnicodeEncodeError, UnicodeDecodeError) as exc:
                offset = sum(len(l) for l in labels[:i]) + i
                raise UnicodeEncodeError(
                    "idna",
                    input,
                    offset + exc.start,
                    offset + exc.end,
                    exc.reason,
                )
        result += trailing_dot
        return result.take_bytes(), len(input)

    def decode(self, input, errors='strict'):

        if errors != 'strict':
            raise UnicodeError(f"Unsupported error handling: {errors}")

        if not input:
            return "", 0

                                                                  
        if not isinstance(input, bytes):
                                            
            input = bytes(input)

        if ace_prefix not in input.lower():
                       
            try:
                return input.decode('ascii'), len(input)
            except UnicodeDecodeError:
                pass

        labels = input.split(b".")

        if labels and len(labels[-1]) == 0:
            trailing_dot = '.'
            del labels[-1]
        else:
            trailing_dot = ''

        result = []
        for i, label in enumerate(labels):
            try:
                u_label = ToUnicode(label)
            except (UnicodeEncodeError, UnicodeDecodeError) as exc:
                offset = sum(len(x) for x in labels[:i]) + len(labels[:i])
                raise UnicodeDecodeError(
                    "idna", input, offset+exc.start, offset+exc.end, exc.reason)
            else:
                result.append(u_label)

        return ".".join(result)+trailing_dot, len(input)

class IncrementalEncoder(codecs.BufferedIncrementalEncoder):
    def _buffer_encode(self, input, errors, final):
        if errors != 'strict':
                                                                     
            raise UnicodeError(f"Unsupported error handling: {errors}")

        if not input:
            return (b'', 0)

        labels = dots.split(input)
        trailing_dot = b''
        if labels:
            if not labels[-1]:
                trailing_dot = b'.'
                del labels[-1]
            elif not final:
                                                                       
                del labels[-1]
                if labels:
                    trailing_dot = b'.'

        result = bytearray()
        size = 0
        for label in labels:
            if size:
                                  
                result.extend(b'.')
                size += 1
            try:
                result.extend(ToASCII(label))
            except (UnicodeEncodeError, UnicodeDecodeError) as exc:
                raise UnicodeEncodeError(
                    "idna",
                    input,
                    size + exc.start,
                    size + exc.end,
                    exc.reason,
                )
            size += len(label)

        result += trailing_dot
        size += len(trailing_dot)
        return (result.take_bytes(), size)

class IncrementalDecoder(codecs.BufferedIncrementalDecoder):
    def _buffer_decode(self, input, errors, final):
        if errors != 'strict':
            raise UnicodeError(f"Unsupported error handling: {errors}")

        if not input:
            return ("", 0)

                                                                  
        if isinstance(input, str):
            labels = dots.split(input)
        else:
                                  
            try:
                input = str(input, "ascii")
            except (UnicodeEncodeError, UnicodeDecodeError) as exc:
                raise UnicodeDecodeError("idna", input,
                                         exc.start, exc.end, exc.reason)
            labels = input.split(".")

        trailing_dot = ''
        if labels:
            if not labels[-1]:
                trailing_dot = '.'
                del labels[-1]
            elif not final:
                                                                       
                del labels[-1]
                if labels:
                    trailing_dot = '.'

        result = []
        size = 0
        for label in labels:
            try:
                u_label = ToUnicode(label)
            except (UnicodeEncodeError, UnicodeDecodeError) as exc:
                raise UnicodeDecodeError(
                    "idna",
                    input.encode("ascii", errors="backslashreplace"),
                    size + exc.start,
                    size + exc.end,
                    exc.reason,
                )
            else:
                result.append(u_label)
            if size:
                size += 1
            size += len(label)

        result = ".".join(result) + trailing_dot
        size += len(trailing_dot)
        return (result, size)

class StreamWriter(Codec,codecs.StreamWriter):
    pass

class StreamReader(Codec,codecs.StreamReader):
    pass

                        

def getregentry():
    return codecs.CodecInfo(
        name='idna',
        encode=Codec().encode,
        decode=Codec().decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamwriter=StreamWriter,
        streamreader=StreamReader,
        _expat_decoding_table=False,
    )
