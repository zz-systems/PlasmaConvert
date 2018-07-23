import sys
import struct
from elftools.elf.elffile import ELFFile
from elftools.construct.lib.container import Container
from elftools.elf.enums import *
MAX_SIZE = (1024*1024*4)

from elftools.construct import (
    UBInt32, Array, Struct
    )

MIPS_RegInfo = Struct("MIPS_RegInfo",
    UBInt32("ri_gprmask"),
    Array(4, UBInt32("ri_cprmask")),
    UBInt32("ri_gp_value")
)

def printContainer(c, depth=1):
    indent = str()
    for i in range(depth):
        indent += "  "
        
    for k,v in c.items():
        if(isinstance(v, Container)):
            print(indent + k + " :")
            printContainer(v, depth+1)
        else:
            if(isinstance(v, int)):
                v = format(v, '08X')
            print(indent + k + " : " + str(v))

def printMem(mem):
    if(len(mem) % 4 != 0):
        print("Not aligned!")
        return

    for x in range(0,len(mem),4):
        v1 = str(format(mem[x], '02X'))
        v2 = str(format(mem[x+1], '02X'))
        v3 = str(format(mem[x+2], '02X'))
        v4 = str(format(mem[x+3], '02X'))
        print("\t",str(format(x, '03')), ":",v1, v2, v3, v4);



def printElfFile(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        print("")
        
        print("ElfHeader:")
        printContainer(ELFFile(f).header)            
        print("")
        
        for sect in ELFFile(f).iter_sections():
            print("")
            print(sect.name)
            printContainer(sect.header)
            printMem(sect.data())

        print("")
        
        for segm in ELFFile(f).iter_segments():
            print("")
            printContainer(segm.header)
            printMem(segm.data())
        print("")

        
def list_copy(dest, dest_idx, src, src_idx, num):
    dest[dest_idx:dest_idx+num] = src[src_idx:src_idx+num] 

def ram_image_vhdl(file_src, file_dest, memory):
    # Modify vhdl source code
    # This part is hardcoded for the specific format of the Plasma Memory VHDL-File
    # The Format consists of 4 Blocks * 64 INIT-Statements * 32 Bytes (= 8 KiB)
    # Each 32-bit memory-word ist divided into the 4 blocks (1 byte each)
    # so reading from the same address in every block results in the 32-bit memory data.

    NUM_BLOCKS = 4
    NUM_INITS = 64
    NUM_BYTES = 32

    vhdl = str()
    with open(file_src, 'r') as f:
        vhdl = f.read()

    #Find 'INIT_00 => X"'
    idx = 0
    idx_list = []
    for i in range(NUM_BLOCKS * NUM_INITS):
        text = "INIT_" + format(i % NUM_INITS, "02X") + " => X\""
        idx = vhdl.find(text, idx)
        if(idx < 0):
            raise ValueError("ERROR: Can't find " + text + " in file!");
        idx_list.append(idx + len(text))


    vhdl_lst = list(vhdl)   # strings are immutable -> convert to list of characters
    for i,e in enumerate(memory):
        text = format(e, "08X")
        index = i // NUM_BYTES
        j = ((NUM_BYTES-1) - (i % NUM_BYTES)) * 2
        list_copy(vhdl_lst, idx_list[index      ] + j, text, 0, 2)
        list_copy(vhdl_lst, idx_list[index +  NUM_INITS] + j, text, 2, 2)
        list_copy(vhdl_lst, idx_list[index + (2 * NUM_INITS)] + j, text, 4, 2)
        list_copy(vhdl_lst, idx_list[index + (3 * NUM_INITS)] + j, text, 6, 2)

    with open(file_dest, 'w') as f:
        f.write("".join(vhdl_lst))

def ram_image_mif(file_dest, memory):
    BLOCKS = 4
    WIDTH = 8
    DEPTH = 2048

    ADDRESS_RADIX = 'HEX'
    DATA_RADIX = 'HEX'

    blocks = [[], [], [], []]
    for i,e in enumerate(memory):
        text = format(e, "08X")
        blocks[0].append(text[0:2])
        blocks[1].append(text[2:4])
        blocks[2].append(text[4:6])
        blocks[3].append(text[6:8])

    for block in range(0, BLOCKS):
        with open(file_dest + "_block_{}.mif".format(block), 'w') as f:
            f.write("-- MEMORY INIT FILE BLOCK {}\n".format(block))
            f.write("WIDTH = {};\n".format(WIDTH))
            f.write("DEPTH = {};\n".format(DEPTH))
            f.write("ADDRESS_RADIX = {};\n".format(ADDRESS_RADIX))
            f.write("DATA_RADIX = {};\n".format(DATA_RADIX))
            f.write("CONTENT\n")
            f.write("BEGIN\n")

            for adr in range(0, DEPTH):
                val = blocks[block][adr] if len(blocks[block]) > adr else 0;
                f.write("{0:08X} : {1:};\n".format(adr, val))

            f.write("END\n")

def doConvert(filename, vhdl_src, vhdl_dest):
    code = bytearray(MAX_SIZE) # TODO: dynamic sizing
    length = 0

    with open(filename, 'rb') as f:
        if(ELFFile(f)["e_entry"] != 0):
            raise ValueError("entry-point needs to be at address 0!")
        if(ELFFile(f).elfclass != 32):
            raise ValueError("ELF needs to be 32-bit!")
        if(ELFFile(f).little_endian):
            raise ValueError("ELF needs to be big endian!")

        for sect in ELFFile(f).iter_sections():
            if(sect["sh_type"] == "SHT_PROGBITS" or sect["sh_type"] == "SHT_NOBITS"):
                print(sect.name)
                start = sect["sh_addr"]
                end = start + sect["sh_size"]
                phys_end = start + sect["sh_size"]

                print("\talign: " + str(sect["sh_addralign"]))
                print("\tstart: " + str(start))
                print("\tend: " + str(end))
                print("\tphys_end: " + str(phys_end))

                if(phys_end >= len(code)):
                    raise ValueError("PROGBITS-Segement to big!")
                code[start:end] = sect.data()
                length = max(length, end)


    memory = []
    for i in range(0,length,4):  
        memory.append(struct.unpack(">L", code[i:i+4])[0])

    with open(filename + ".txt", 'w') as f:
        for e in memory:
            f.write(format(e, "08X") + "\n")

    #ram_image_vhdl(vhdl_src, vhdl_dest, memory)
    ram_image_mif(vhdl_dest, memory)

            
if __name__ == '__main__':
    src, vhdl_src, vhdl_dest = sys.argv[1:4]

    #printElfFile(src)
    doConvert(src, vhdl_src, vhdl_dest)
