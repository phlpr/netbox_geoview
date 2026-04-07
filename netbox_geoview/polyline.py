def decode_polyline(shape, precision=6):
    coordinates = []
    lat = 0
    lon = 0
    index = 0
    factor = 10**precision

    while index < len(shape):
        shift = 0
        result = 0
        while True:
            if index >= len(shape):
                return coordinates
            chunk = ord(shape[index]) - 63
            index += 1
            result |= (chunk & 0x1F) << shift
            shift += 5
            if chunk < 0x20:
                break
        lat += ~(result >> 1) if result & 1 else result >> 1

        shift = 0
        result = 0
        while True:
            if index >= len(shape):
                return coordinates
            chunk = ord(shape[index]) - 63
            index += 1
            result |= (chunk & 0x1F) << shift
            shift += 5
            if chunk < 0x20:
                break
        lon += ~(result >> 1) if result & 1 else result >> 1

        coordinates.append([lat / factor, lon / factor])

    return coordinates
