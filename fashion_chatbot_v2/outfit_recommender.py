class OutfitRecommender:
    def __init__(self, rag_engine):
        self.rag = rag_engine

    def recommend_full_outfit(self, gender, occasion, budget=None):
        """Gợi ý một set đồ hoàn chỉnh"""
        outfit_data = self.rag.suggest_outfit(gender, occasion)
        if not outfit_data:
            return {"error": "Không tìm thấy set đồ phù hợp"}

        items = outfit_data["items"]
        if budget:
            items = [i for i in items if i["price"] <= budget]

        total = sum(i["price"] for i in items)
        return {
            "rule_name": outfit_data["rule"]["name"],
            "tips": outfit_data["rule"]["tips"],
            "items": items,
            "total_price": total,
            "item_count": len(items),
        }

    def format_outfit_text(self, outfit_result):
        """Format kết quả thành text đẹp"""
        if "error" in outfit_result:
            return outfit_result["error"]

        lines = [f"✨ **{outfit_result['rule_name']}**"]
        lines.append(f"💡 *{outfit_result['tips']}*\n")
        lines.append("**Các món gợi ý:**")
        for i, item in enumerate(outfit_result["items"], 1):
            lines.append(
                f"{i}. [{item['id']}] {item['name']} - "
                f"{item['price']:,}đ - ⭐ {item['rating']}"
            )
        lines.append(f"\n💰 **Tổng: {outfit_result['total_price']:,}đ**")
        return "\n".join(lines)