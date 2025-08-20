class Calculator:
    @staticmethod
    def cost_per_unit(cost: float, units: float) -> float:
        if units <= 0:
            raise ValueError("Units must be > 0.")
        return cost / units

    @staticmethod
    def calculate_revenue(price: float, cookie_yield: float) -> float:
        if price < 0 or cookie_yield < 0:
            raise ValueError("Price and yield must be non-negative.")
        return price * cookie_yield

    @staticmethod
    def calculate_total_cost(df) -> float:
        if df.empty:
            return 0.0
        totals = df["unit_cost"] * df["quantity_used"]
        return float(totals.sum())

    @staticmethod
    def calculate_profit(revenue: float, total_cost: float) -> float:
        return revenue - total_cost

    @staticmethod
    def profit_per_cookie(profit: float, cookie_yield: float) -> float:
        if cookie_yield <= 0:
            raise ValueError("Cookies per batch must be > 0 for per-cookie profit.")
        return profit / cookie_yield