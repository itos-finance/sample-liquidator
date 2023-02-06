from math import log, sqrt
import numpy as np
import matplotlib.pyplot as plt

TICK_BASE = log(1.0001)
MIN_TICK = -887272
MAX_TICK = -MIN_TICK

def tick_to_price(tick):
    return 1.0001 ** tick


class PoolRepresentation:
    def __init__(self, init_price):
        self.price = init_price
        self.mliqs = [0] * (MAX_TICK - MIN_TICK)
        self.tliqs = [0] * (MAX_TICK - MIN_TICK)

    def get_price(self):
        return self.price

    def get_raw_liqs(self, low_price, high_price, tick_interval, isM):
        low_tick = int(log(low_price) / TICK_BASE)
        high_tick = int(log(high_price) / TICK_BASE)
        liqs = self.mliqs if isM else self.tliqs
        return [liqs[i] for i in range(low_tick, high_tick, tick_interval)]

    def get_liqs(self, low_price, high_price, tick_interval):
        factor = 1.0001 ** tick_interval
        tick_width = log(high_price / low_price) / TICK_BASE
        inc_width = int(tick_width // tick_interval)
        prices = [low_price] * inc_width
        for i in range(1, len(prices)):
            prices[i] = prices[i-1] * factor
        mliqs = self.get_raw_liqs(low_price, high_price, tick_interval, True)
        tliqs = self.get_raw_liqs(low_price, high_price, tick_interval, False)
        return list(zip(prices, mliqs, tliqs))

    def add_liq(self, low_tick, high_tick, liq, isM):
        liqs = self.mliqs if isM else self.tliqs
        for i in range(low_tick, high_tick):
            liqs[i] += liq

    def add_event(self, web3_event_log):
        args = web3_event_log.args
        if (web3_event_log.event == "AddTLiq"):
            self.add_liq(args.lowTick, args.upperTick, args.liq, False)
        elif (web3_event_log.event == "AddMLiq"):
            self.add_liq(args.lowTick, args.upperTick, args.liq, True)
        elif (web3_event_log.event == 'Swap'):
            self.price = (args.newPrice / (1 << 96)) ** 2
        elif (web3_event_log.event == "AddTLiqShort"):
            self.add_liq(args.lowTick, args.upperTick, args.liq, False)
        elif (web3_event_log.event == "AddMLiqShort"):
            self.add_liq(args.lowTick, args.upperTick, args.liq, True)


class Position:

    def set_init_val(self, init_price):
        self.init_value = self.value_at(init_price)

    def get_delta_from(self, price):
        return self.value_at(price) - self.init_value

class Naked(Position):
    def __init__(self):
        self.exposure = 0
        self.init_value = 0

    def value_at(self, price):
        return self.exposure * price

    def add_event(self, price, event_args):
        expo = self.get_exposure(event_args)
        self.exposure += expo
        self.init_value += price * expo


class Long(Naked):
    def get_exposure(self, event_args):
        return event_args.xAmount


class Short(Naked):
    def get_exposure(self, event_args):
        return -event_args.xAmount


class AMMPosition(Position):

    def __init__(self, low_tick, high_tick, liq):
        super().__init__()
        self.lt = low_tick
        self.ht = high_tick
        self.liq = liq
        self.low_sqrt = 1.0001 ** (low_tick // 2)
        self.high_sqrt = 1.0001 ** (high_tick // 2)

    @classmethod
    def from_event(cls, price, event_args):
        return cls(price, event_args.lowTick, event_args.upperTick, event_args.liq)

    def get_price_range(self):
        return (self.low_sqrt ** 2, self.high_sqrt ** 2)

    def get_liq(self):
        return self.liq


class Taker(AMMPosition):
    def __init__(self, init_price, low_tick, high_tick, liq):
        super().__init__(low_tick, high_tick, liq)
        self.under_ys = liq * (self.high_sqrt - self.low_sqrt)
        self.inv_low_sqrt = 1 / self.low_sqrt
        self.over_xs = liq * (self.inv_low_sqrt - 1 / self.high_sqrt)
        self.set_init_val(init_price)

    def value_at(self, price):
        sqrt_price = sqrt(price)
        if (sqrt_price < self.low_sqrt):
            return self.under_ys
        elif (sqrt_price >= self.high_sqrt):
            return price * self.over_xs
        else:
            return (price * self.liq * (self.inv_low_sqrt - 1 / sqrt_price) +
                    self.liq * (self.high_sqrt - sqrt_price))


class TakerPut(Taker):
    def value_at(self, price):
        return super().value_at(price) - self.over_xs * price


class Maker(AMMPosition):
    def __init__(self, init_price, low_tick, high_tick, liq):
        super().__init__(low_tick, high_tick, liq)
        self.over_ys = liq * (self.high_sqrt - self.low_sqrt)
        self.inv_high_sqrt = 1 / self.high_sqrt
        self.under_xs = liq * (1 / self.low_sqrt - self.inv_high_sqrt)
        self.set_init_val(init_price)

    def value_at(self, price):
        sqrt_price = sqrt(price)
        if (sqrt_price < self.low_sqrt):
            return price * self.under_xs
        elif (sqrt_price >= self.high_sqrt):
            return self.over_ys
        else:
            return (price * self.liq * (1 / sqrt_price - self.inv_high_sqrt) +
                    self.liq * (sqrt_price - self.low_sqrt))


class MakerCall(Maker):
    def value_at(self, price):
        return super().value_at(price) - price * self.under_xs


class PositionRepresentation:
    def __init__(self, pool):
        self.pool = pool
        self.makers = {}
        self.takers = {}
        self.shorts = Short()
        self.longs = Long()

    def add_event(self, web3_event_log):
        price = self.pool.get_price()
        if (web3_event_log.event == "AddTLiq"):
            newTaker = Taker.from_event(price, web3_event_log.args)
            self.takers[newTaker.get_price_range()] = newTaker
        elif (web3_event_log.event == "AddMLiq"):
            newMaker = Maker.from_event(price, web3_event_log.args)
            self.makers[newMaker.get_price_range()] = newMaker
        elif (web3_event_log.event == "AddTLiqShort"):
            newTaker = TakerPut.from_event(price, web3_event_log.args)
            self.takers[newTaker.get_price_range()] = newTaker
        elif (web3_event_log.event == "AddMLiqShort"):
            newMaker = MakerCall.from_event(price, web3_event_log.args)
            self.makers[newMaker.get_price_range()] = newMaker
        elif (web3_event_log.event == "Short"):
            self.shorts.add_event(price, web3_event_log.args)
        elif (web3_event_log.event == "Long"):
            self.longs.add_event(price, web3_event_log.args)
        else:
            pass

    def get_fee_ranges(self):
        pairs = ([(k, p.liq) for k, p in self.makers.items()] +
                 [(k, -p.liq) for k, p in self.takers.items()])
        if not pairs:
            return []
        ranges, liqs = self.flatten_fee_ranges(pairs)

        max_liq = max(map(abs, liqs))
        liqs = [l / max_liq for l in liqs]
        return [(p[0], p[1], l) for (p, l) in zip(ranges, liqs)]

    @staticmethod
    def flatten_fee_ranges(fee_data):
        deltas = []
        for (k, l) in fee_data:
            start, stop = k
            deltas.append((start, l))
            deltas.append((stop, -l))

        deltas = sorted(deltas)
        last = None
        current = 0
        keys = []
        liqs = []
        for price, liq in deltas:
            if current != 0:
                keys.append((last, price))
                liqs.append(liq)
            current += liq
            last = price
        return keys, liqs

    def get_values_at(self, low_price, high_price, inc):
        prices = list(map(float, np.arange(low_price, high_price, inc)))
        res = []
        for position_dict in (self.makers, self.takers):
            for pos in position_dict.values():
                res.append([pos.value_at(p) for p in prices])
        res.append([self.shorts.value_at(p) for p in prices])
        res.append([self.longs.value_at(p) for p in prices])
        return {"prices": prices, "positions": res}

    def get_deltas_from(self, low_price, high_price, inc):
        prices = list(map(float, np.arange(low_price, high_price, inc)))
        res = []
        for position_dict in (self.makers, self.takers):
            for pos in position_dict.values():
                res.append([pos.get_delta_from(p) for p in prices])
        res.append([self.shorts.get_delta_from(p) for p in prices])
        res.append([self.longs.get_delta_from(p) for p in prices])
        return {"prices": prices, "positions": res}
