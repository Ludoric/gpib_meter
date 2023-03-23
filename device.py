class SimpleDevice:
    """
    Class for GPIB devices that can be configured and read from
    Example use:
        import pyvisa
        rm = pyvisa.ResourceManager('@py')
        amps = Device(rm, 'GPIB::14',
                      ['*rst; status:preset; *cls', 'CONFIGURE:CURRENT:DC'],
                      'READ?', cast=float)
        ...
        current = amps.read()

    
    Arguments:
        resourceID = GPIO port string
        configuration = list of strings sent as configuration
        read = string used to query device for data
        cast = function used to cast read data
        titles = names for the outputs of cast
        set = dict of (lowercase) name to set, 
    """
    def __init__(self, resourceManager, resourceID, *, config,
                 read, cast, titles, setthing={None: ''}):
        """
            titles, device, read, set are the only methods and fields that
            should be visible
        """
        self._rm = resourceManager
        self._rID = resourceID
        self._config = config
        self._read = read
        self._cast = cast
        self.titles = titles
        self._setthing = setthing
        self.device = self._rm.open_resource(self._rID)
        [self.device.write(c) for c in self._config]

    def read(self):
        res = []
        for r in self._read:
            if r:
                self.device.write(r)
            res.append(self.device.read())
        return self._cast(res)


    def set(self, toSet, val=None):
        if val is None:
            self.device.write(self._setthing[toSet])
        else:
            self.device.write(self._setthing[toSet].format(val))

