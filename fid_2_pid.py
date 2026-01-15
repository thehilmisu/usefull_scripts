def fid_2_pid(frame_id):
    """ Update a frame identifier with its parity bits.
    Args:
        frame_id (byte): the frame id to be converted to protected fid.
    Returns:
        byte: the protected frame identifier.
    """
    parity_b0 = 0
    parity_b1 = 0
    # P0 = ID0 xor ID1 xor ID2 xor ID4
    parity_b0 = (bool(frame_id & (1 << 0)) ^
                 bool(frame_id & (1 << 1)) ^
                 bool(frame_id & (1 << 2)) ^
                 bool(frame_id & (1 << 4)))
    # P1 = ~(ID1 xor ID3 xor ID4 xor ID5)
    parity_b1 = (bool(frame_id & (1 << 1)) ^
                 bool(frame_id & (1 << 3)) ^
                 bool(frame_id & (1 << 4)) ^
                 bool(frame_id & (1 << 5)))
    parity_b1 = not parity_b1
    # delete two most significant bits
    frame_pid = 0x3f & frame_id
    # add parity bits
    if parity_b0:
        frame_pid |= (1 << 6)
    if parity_b1:
        frame_pid |= (1 << 7)
    return frame_pid


fid= 0x34
print(fid_2_pid(fid))
print(hex(fid_2_pid(fid)))
