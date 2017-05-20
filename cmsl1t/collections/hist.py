import collections
import bisect
from exceptions import RuntimeError, KeyError, NotImplementedError


class DimensionBase():
    overflow = "overflow"
    underflow = "underflow"

    def __len__(self):
        return self.n_bins


class DimensionSorted(DimensionBase):
    import bisect

    def __init__(self, bin_edges):
        self.bins = sorted(bin_edges)
        self.n_bins = len(self.bins)

    def __getitem__(self, value):
        if value < self.bins[0]:
            found_bin = self.underflow
        elif value >= self.bins[-1]:
            found_bin = self.overflow
        else:
            found_bin = bisect.bisect(self.bins, value) - 1
        return [found_bin]


class DimensionOverlappingBins(DimensionBase):
    def __init__(self, bins):
        self.bins = bins
        self.n_bins = len(self.bins)

    def __getitem__(self, value):
        contained_in = []
        for i, (bin_low, bin_high) in enumerate(self.bins):
            if value >= bin_low and value < bin_high:
                contained_in.append(i)
        if len(contained_in) == 0:
            contained_in = [self.overflow]
        return contained_in


class DimensionRegion(DimensionBase):
    from cmsl1t.geometry import eta_regions

    def __init__(self):
        self.n_bins = len(self.eta_regions)

    def __getitem__(self, value):
        regions = []
        for region, is_contained in self.eta_regions.iteritems():
            if is_contained(value):
                regions.append(region)
        return regions


class HistogramCollection(object):
    '''
    The histogram collection needs a few things:
     - it needs to be able to essentially have binned maps of histograms
     - needs to know how to create new histograms
    '''

    def __init__(self, dimensions, histogram_factory):
        '''
            Should dimensions include or exclude histogram names?
        '''
        if not isinstance(dimensions, list):
            dimensions = [dimensions]
        for dim in dimensions:
            if not isinstance(dim, DimensionBase):
                raise RuntimeError("non-Dimension object given to histogram")
        self._dimensions = dimensions
        self._hists = collections.defaultdict(histogram_factory)

    @classmethod
    def _flatten_bins(self, bins):
        flattened_bins = []
        for dimension in bins:
            if len(flattened_bins) == 0:
                for index in dimension:
                    flattened_bins.append([index])
            else:
                new_bins = []
                for previous in flattened_bins:
                    new_bins += [previous+[index] for index in dimension]
                flattened_bins = new_bins
        output_bin_list = []
        for bin in flattened_bins:
            output_bin_list.append(tuple(bin))
        return output_bin_list

    def _find_bins(self, keys):
        # In python 3.3, this becomes collections.abc.Sequence
        if not isinstance(keys, collections.Sequence):
            if len(self._dimensions) > 1:
                msg = "Single key given when "+len(self._dimensions)+" needed"
                raise KeyError(msg)
            keys = [keys]
        elif len(self._dimensions) != len(keys):
            msg = "Number of keys does not match no. of dimensions\n"
            msg += "Given {0}, needed {1}".format(
                    len(keys), len(self._dimeesions))
            raise KeyError(msg)

        # Check every dimension if it contains these values
        bins = []
        for key, dimension in zip(keys, self._dimensions):
            bins.append(dimension[key])

        # Some dimensions might return multiple values, flatten returned arrays
        bins = self._flatten_bins(bins)

        return bins

    def __getitem__(self, keys):
        '''
            Supposed to handle
                coll[x]
            and
                coll[x, y, z]
        '''
        hist_indices = self._find_bins(keys)
        if len(hist_indices) > 1:
            msg = """HistogramCollection.__getitem__ not fully implemented for
                   dimensions with overlapping bins"""
            raise NotImplementedError(msg)
        return self._hists[hist_indices[0]]

    def __setitem__(self, keys, value):
        '''
            Supposed to handle
                coll[x]
            and
                coll[x, y, z]
        '''
        index_list = self._find_bins(keys)
        for indices in index_list:
            self._hists[indices] = value

    def shape(self):
        _shape = [len(dim) for dim in self._dimensions]
        return tuple(_shape)

    def __len__(self):
        return len(self._dimensions[0])