import matplotlib.pyplot as plt

class Plotter:
    def __init__(self, llp):
        self.llp = llp

    def plot(self):
        data = self.llp.produce()
        num_subs = len(data['subscriptions'])

        plt.subplot(num_subs + 1, 1, 1)
        prices, makers, takers = zip(*data["liquidity"])
        plt.plot(prices, makers)
        plt.plot(prices, takers)

        i = 2
        for wallet, data in data['subscriptions'].items():
            plt.subplot(num_subs + 1, 1, i)
            i += 1

            values = data['value']
            if ("positions" in values):
                summed_plot = list(map(sum, zip(*values["positions"])))
                plt.plot(values["prices"], summed_plot)

        plt.show()
