import json
import re
import unicodedata


class RAGEngine:
    def __init__(self):
        with open("data/products.json", "r", encoding="utf-8") as f:
            self.products = json.load(f)
        with open("data/size_chart.json", "r", encoding="utf-8") as f:
            self.size_chart = json.load(f)
        with open("data/style_rules.json", "r", encoding="utf-8") as f:
            self.style_rules = json.load(f)["rules"]
        with open("data/occasions.json", "r", encoding="utf-8") as f:
            self.occasions = json.load(f)["occasions"]

        print(f"[INFO] Đã load {len(self.products)} sản phẩm, "
              f"{len(self.style_rules)} luật phối đồ")

    # ============================================================
    # 1. TIỀN XỬ LÝ - BỎ DẤU ĐỂ SO SÁNH ROBUST
    # ============================================================
    def _strip_accents(self, text):
        """Bỏ dấu tiếng Việt. VD: 'đầm' -> 'dam'"""
        text = text.replace('đ', 'd').replace('Đ', 'D')
        nfkd = unicodedata.normalize('NFD', text)
        return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')

    def _normalize(self, text):
        """Chuẩn hóa: lowercase, bỏ dấu câu"""
        text = text.lower().strip()
        text = re.sub(r'[?!.,;:]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def _has_any(self, text, keywords):
        """Kiểm tra text (không dấu) có chứa keyword không"""
        text_na = self._strip_accents(text.lower())
        for kw in keywords:
            kw_na = self._strip_accents(kw.lower())
            if kw_na in text_na:
                return True
        return False

    # ============================================================
    # 2. TRÍCH XUẤT THỰC THỂ (ENTITY EXTRACTION)
    # ============================================================
    def extract_height(self, text):
        """Chiều cao. VD: '1m70' -> 170, '170cm' -> 170"""
        match = re.search(r'(\d)\s*m\s*(\d{1,2})', text)
        if match:
            meter = int(match.group(1))
            cm = int(match.group(2))
            if cm < 10:
                cm = cm * 10
            return meter * 100 + cm
        match = re.search(r'(\d{3})\s*cm', text)
        if match:
            return int(match.group(1))
        match = re.search(r'\b(1[4-9]\d)\b', text)
        if match:
            return int(match.group(1))
        return None

    def extract_weight(self, text):
        """Cân nặng. VD: '60kg' -> 60"""
        match = re.search(r'(\d{2,3})\s*(kg|ki|ky)', self._strip_accents(text))
        if match:
            return int(match.group(1))
        if self._has_any(text, ['nang', 'can']):
            match = re.search(r'\b(\d{2,3})\b', text)
            if match:
                return int(match.group(1))
        return None

    def extract_gender(self, text):
        """Giới tính - dùng regex CÓ DẤU để tránh nhầm 'có' vs 'cô'"""
        text_lower = text.lower()
        # Nam
        for pattern in [r'\bnam\b', r'\banh\b', r'\bchú\b', r'\bông\b',
                        r'\bbố\b', r'\bcon trai\b', r'\bba\b']:
            if re.search(pattern, text_lower):
                return 'Nam'
        # Nữ
        for pattern in [r'\bnữ\b', r'\bem gái\b', r'\bchị\b', r'\bcô\b',
                        r'\bbà\b', r'\bmẹ\b', r'\bcon gái\b', r'\bmá\b']:
            if re.search(pattern, text_lower):
                return 'Nữ'
        return None

    def extract_budget(self, text):
        """Ngân sách. VD: '500k' -> 500000, 'dưới 500.000'"""
        match = re.search(r'(\d+)\s*(k|nghin|ngan)', self._strip_accents(text))
        if match:
            return int(match.group(1)) * 1000
        match = re.search(r'(\d{1,3}(?:\.\d{3})+|\d{6,7})', text)
        if match:
            try:
                return int(match.group(1).replace('.', ''))
            except:
                pass
        return None

    def extract_occasion(self, text):
        """Dịp sử dụng"""
        keyword_map = {
            'Đi làm': ['di lam', 'cong so', 'di hop', 'lam viec', 'van phong'],
            'Đi học': ['di hoc', 'sinh vien', 'hoc sinh', 'truong hoc'],
            'Đi chơi': ['di choi', 'dao pho', 'tu tap', 'gap ban'],
            'Cafe': ['cafe', 'ca phe', 'uong cafe', 'ngoi quan'],
            'Dự tiệc': ['du tiec', 'tiec', 'su kien', 'dam cuoi', 'cuoi'],
            'Hẹn hò': ['hen ho', 'hen gap', 'di hen'],
            'Du lịch': ['du lich', 'nghi duong', 'di xa'],
            'Đi biển': ['di bien', 'tam bien', 'bai bien', 'di boi', 'boi loi'],
            'Thể thao': ['the thao', 'tap gym', 'tap luyen', 'chay bo', 'yoga'],
            'Dạo phố': ['dao pho', 'di dao', 'mua sam'],
            'Ở nhà': ['o nha', 'tai nha', 'thu gian'],
            'Club': ['club', 'bar', 'hop dem'],
        }
        text_na = self._strip_accents(text.lower())
        for occasion, keywords in keyword_map.items():
            for kw in keywords:
                if kw in text_na:
                    return occasion
        return None

    def extract_season(self, text):
        """Mùa"""
        text_na = self._strip_accents(text.lower())
        if any(kw in text_na for kw in ['mua dong', 'dong', 'lanh', 'gia ret', 'mua lanh']):
            return 'Đông'
        if any(kw in text_na for kw in ['mua he', 'mua ha', 'nong buc', 'mua nong']):
            return 'Hạ'
        if any(kw in text_na for kw in ['mua xuan', 'xuan', 'am ap']):
            return 'Xuân'
        if any(kw in text_na for kw in ['mua thu', 'thu', 'mat me']):
            return 'Thu'
        return None

    def extract_product_types(self, text):
        """
        Trả về LIST các loại sản phẩm user muốn.
        VD: 'quần áo' -> ['áo', 'quần']
        """
        type_map = {
            'áo sơ mi': ['so mi', 'somi'],
            'áo thun': ['ao thun', 't-shirt', 'tshirt'],
            'áo polo': ['polo'],
            'áo khoác': ['ao khoac', 'khoac', 'jacket'],
            'áo hoodie': ['hoodie'],
            'áo len': ['ao len'],
            'áo vest': ['ao vest'],
            'áo blazer': ['blazer'],
            'áo croptop': ['croptop', 'crop top'],
            'áo ba lỗ': ['ba lo'],
            'áo gile': ['gile'],
            'đầm': ['dam', 'dress'],
            'chân váy': ['chan vay'],
            'váy': ['vay'],
            'quần jeans': ['jeans', 'quan bo'],
            'quần tây': ['quan tay', 'quan au'],
            'quần short': ['quan short', 'quan ngan'],
            'quần jogger': ['jogger'],
            'quần legging': ['legging'],
            'quần baggy': ['baggy'],
        }

        text_na = self._strip_accents(text.lower())
        matched_types = []

        # Sort theo length giảm dần để ưu tiên cụ thể
        sorted_types = sorted(type_map.items(), key=lambda x: -len(x[0]))

        for ptype, keywords in sorted_types:
            for kw in keywords:
                # Dùng regex để match từ độc lập
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text_na):
                    if ptype not in matched_types:
                        matched_types.append(ptype)
                    break

        # ⭐ Xử lý đặc biệt: "quần áo" -> cả 2 loại
        if self._has_any(text_na, ['quan ao']):
            if 'áo' not in matched_types:
                # Nhưng chỉ thêm 'áo' nếu chưa match áo cụ thể
                if not any(t.startswith('áo') for t in matched_types):
                    matched_types.append('áo')
            if 'quần' not in matched_types:
                if not any(t.startswith('quần') for t in matched_types):
                    matched_types.append('quần')

        # Nếu match "áo sơ mi" thì cũng coi như có "áo"
        if any(t.startswith('áo') for t in matched_types) and 'áo' not in matched_types:
            matched_types.append('áo')

        return matched_types

    def extract_product_type(self, text):
        """Wrapper cũ - trả về loại đầu tiên (giữ tương thích)"""
        types = self.extract_product_types(text)
        return types[0] if types else None

    def extract_color(self, text):
        """Màu sắc"""
        text_na = self._strip_accents(text.lower())
        colors = ['trang', 'den', 'do', 'xanh', 'hong', 'be', 'nau', 'xam', 'vang', 'tim', 'cam']
        for color in colors:
            if color in text_na:
                return color
        return None

    # ============================================================
    # 3. PHÂN LOẠI Ý ĐỊNH (INTENT DETECTION)
    # ============================================================
    def detect_intent(self, text):
        text_na = self._strip_accents(text.lower())
        height = self.extract_height(text)
        weight = self.extract_weight(text)
        occasion = self.extract_occasion(text)
        product_types = self.extract_product_types(text)
        season = self.extract_season(text)

        # Tư vấn size (cần height + weight)
        if height and weight:
            return 'SIZE_ADVICE'

        # Tư vấn phối đồ
        if self._has_any(text_na, ['phoi do', 'mac gi', 'mix', 'set do', 'outfit']):
            return 'OUTFIT_ADVICE'

        # So sánh
        if self._has_any(text_na, ['so sanh', 'khac gi', 'nen chon']):
            return 'COMPARE'

        # Hỏi giá
        if self._has_any(text_na, ['gia', 'bao nhieu']):
            return 'PRICE_INQUIRY'

        # Tìm sản phẩm (có product_type HOẶC occasion HOẶC season)
        if product_types or occasion or season:
            return 'PRODUCT_SEARCH'

        if self._has_any(text_na, ['tim', 'mua', 'muon', 'can', 'goi y', 'gioi thieu']):
            return 'PRODUCT_SEARCH'

        # Chào hỏi
        if self._has_any(text_na, ['chao', 'hello', 'hi', 'xin chao']):
            return 'GREETING'

        return 'UNKNOWN'

    # ============================================================
    # 4. TÌM KIẾM SẢN PHẨM (MULTI-CRITERIA SEARCH)
    # ============================================================
    def search_products(self, gender=None, occasion=None, product_types=None,
                        color=None, budget_max=None, season=None, limit=5):
        """
        Tìm sản phẩm theo nhiều tiêu chí.
        product_types: LIST các loại (VD: ['áo', 'quần'])
        """
        results = self.products.copy()

        # Filter giới tính
        if gender:
            results = [p for p in results if p["gender"] in (gender, "Unisex")]

        # Filter mùa
        if season:
            results = [p for p in results if season in p.get("season", [])]

        # Filter dịp
        if occasion:
            occ_na = self._strip_accents(occasion.lower())
            results = [p for p in results
                       if any(occ_na in self._strip_accents(o.lower())
                              for o in p.get("occasion", []))]

        # Filter loại sản phẩm (hỗ trợ LIST)
        if product_types:
            filtered = []
            for p in results:
                cat_na = self._strip_accents(p["category"].lower())
                for ptype in product_types:
                    pt_na = self._strip_accents(ptype.lower())
                    if pt_na in cat_na:
                        filtered.append(p)
                        break
            results = filtered

        # Filter màu
        if color:
            color_na = self._strip_accents(color.lower())
            results = [p for p in results
                       if color_na in self._strip_accents(p["color"].lower())]

        # Filter ngân sách
        if budget_max:
            results = [p for p in results if p["price"] <= budget_max]

        # Sort theo rating
        results = sorted(results, key=lambda x: x.get("rating", 0), reverse=True)
        return results[:limit]

    # ============================================================
    # 5. TƯ VẤN SIZE
    # ============================================================
    def get_size_chart_for(self, gender, product_type="Ao"):
        gender = gender.strip().capitalize()
        if gender in self.size_chart:
            chart = self.size_chart[gender]
            if isinstance(chart, dict) and product_type in chart:
                return chart[product_type]
            if isinstance(chart, list):
                return chart
        return self.size_chart.get("Unisex", [])

    def _determine_chart_type(self, product_types):
        """Xác định loại bảng size cần dùng"""
        if not product_types:
            return "Ao"
        # Kiểm tra từng loại
        for pt in product_types:
            if any(x in pt for x in ['quần jeans', 'quần tây', 'quần short', 'quần baggy']):
                return "Quan"
            if any(x in pt for x in ['đầm', 'váy', 'chân váy']):
                return "Vay"
        return "Ao"

    def suggest_size(self, gender, height, weight, product_type="Ao"):
        chart = self.get_size_chart_for(gender, product_type)
        matched = []
        for item in chart:
            h_min, h_max = item["height"]
            w_min, w_max = item["weight"]
            if h_min <= height <= h_max and w_min <= weight <= w_max:
                matched.append(item["size"])
        if not matched:
            best, best_diff = None, float("inf")
            for item in chart:
                h_mid = sum(item["height"]) / 2
                w_mid = sum(item["weight"]) / 2
                diff = abs(h_mid - height) + abs(w_mid - weight)
                if diff < best_diff:
                    best_diff, best = diff, item["size"]
            matched = [best] if best else []
        return matched

    def _explain_size(self, gender, height, weight, chart_type, sizes):
        """Giải thích lý do chọn size"""
        chart = self.get_size_chart_for(gender, chart_type)
        explanation = f"📊 **Bảng size {chart_type} — {gender}:**\n"
        for item in chart:
            h_range = f"{item['height'][0]}-{item['height'][1]}cm"
            w_range = f"{item['weight'][0]}-{item['weight'][1]}kg"
            mark = " ✅" if item['size'] in sizes else ""
            explanation += f"   • Size {item['size']}: {h_range}, {w_range}{mark}\n"
        return explanation

    # ============================================================
    # 6. GỢI Ý PHỐI ĐỒ
    # ============================================================
    def suggest_outfit(self, gender, occasion):
        if not gender or not occasion:
            return None
        matched_rules = [
            r for r in self.style_rules
            if r["gender"].lower() in (gender.lower(), "unisex")
            and occasion.lower() in r["occasion"].lower()
        ]
        if not matched_rules:
            return None
        outfit = {"rule": matched_rules[0], "items": []}
        for item_type in matched_rules[0]["items"]:
            candidates = [
                p for p in self.products
                if item_type.lower() in p["category"].lower()
                and p["gender"].lower() in (gender.lower(), "unisex")
            ]
            if candidates:
                best = sorted(candidates, key=lambda x: x.get("rating", 0), reverse=True)[0]
                outfit["items"].append(best)
        return outfit

    # ============================================================
    # 7. FORMAT & RESPONSE
    # ============================================================
    def _format_product(self, p):
        return (
            f"**[{p['id']}] {p['name']}**\n"
            f"   💰 Giá: {p['price']:,}đ\n"
            f"   📏 Size: {', '.join(p['sizes'])}\n"
            f"   🎨 Màu: {p['color']} | 🧵 {p['material']}\n"
            f"   ⭐ Đánh giá: {p['rating']}/5 ({p.get('sold', 0)} đã bán)\n"
            f"   📝 {p['description']}"
        )

    def _response_size_advice(self, text, gender, height, weight):
        if not height or not weight:
            return ("Để tư vấn size chính xác, bạn vui lòng cung cấp:\n"
                    "- 📏 Chiều cao (ví dụ: 1m70)\n"
                    "- ⚖️ Cân nặng (ví dụ: 60kg)")

        if not gender:
            gender = "Nữ"

        product_types = self.extract_product_types(text)
        chart_type = self._determine_chart_type(product_types)

        sizes = self.suggest_size(gender, height, weight, chart_type)
        if not sizes:
            return f"Xin lỗi, tôi chưa có bảng size phù hợp cho {gender}."

        size_str = ", ".join(sizes)
        response = f"📏 **Tư vấn size cho {gender}**\n\n"
        response += f"Với chiều cao **{height}cm** và cân nặng **{weight}kg**, "
        response += f"bạn phù hợp với size: **{size_str}**\n\n"

        # Giải thích logic
        response += self._explain_size(gender, height, weight, chart_type, sizes)
        response += "\n"

        # Tìm sản phẩm theo nhu cầu
        occasion = self.extract_occasion(text)
        season = self.extract_season(text)
        budget = self.extract_budget(text)
        color = self.extract_color(text)

        products = self.search_products(
            gender=gender,
            occasion=occasion,
            product_types=product_types if product_types else None,
            color=color,
            budget_max=budget,
            season=season,
            limit=5
        )

        # Fallback: giảm tiêu chí
        if len(products) < 3 and occasion:
            products = self.search_products(
                gender=gender, product_types=product_types,
                season=season, budget_max=budget, limit=5)

        if len(products) < 3 and product_types:
            products = self.search_products(
                gender=gender, occasion=occasion,
                season=season, budget_max=budget, limit=5)

        if len(products) < 3 and season:
            products = self.search_products(
                gender=gender, product_types=product_types,
                occasion=occasion, budget_max=budget, limit=5)

        if products:
            response += f"🎁 **Gợi ý {len(products)} sản phẩm phù hợp:**\n\n"
            for p in products:
                response += self._format_product(p) + "\n\n"

        return response.strip()

    def _response_outfit_advice(self, text, gender, occasion):
        if not occasion:
            return ("Để gợi ý phối đồ, bạn cho tôi biết dịp sử dụng nhé:\n"
                    "💼 Đi làm | 🎉 Đi chơi | ☕ Cafe | 🥂 Dự tiệc | 🏃 Thể thao | ✈️ Du lịch")

        if not gender:
            gender = "Nữ"

        outfit = self.suggest_outfit(gender, occasion)
        if not outfit:
            return f"Xin lỗi, tôi chưa có gợi ý phối đồ cho dịp **{occasion}** với {gender}."

        response = f"✨ **Set đồ gợi ý — {outfit['rule']['name']}**\n\n"
        response += f"💡 *{outfit['rule']['tips']}*\n\n"
        response += "**Các món trong set:**\n\n"

        total = 0
        for i, p in enumerate(outfit["items"], 1):
            response += f"{i}. {self._format_product(p)}\n\n"
            total += p["price"]

        response += f"---\n💰 **Tổng tiền: {total:,}đ**"
        return response

    def _response_product_search(self, text, gender, occasion, budget, season, product_types):
        color = self.extract_color(text)

        products = self.search_products(
            gender=gender,
            occasion=occasion,
            product_types=product_types if product_types else None,
            color=color,
            budget_max=budget,
            season=season,
            limit=5
        )

        # Fallback giảm tiêu chí
        if not products:
            if occasion:
                products = self.search_products(
                    gender=gender, occasion=occasion, season=season, limit=5)
            elif product_types:
                products = self.search_products(
                    gender=gender, product_types=product_types, season=season, limit=5)
            elif season:
                products = self.search_products(
                    gender=gender, season=season, limit=5)
            elif color:
                products = self.search_products(
                    gender=gender, color=color, limit=5)

        if not products:
            return ("Xin lỗi, tôi chưa tìm thấy sản phẩm phù hợp với yêu cầu của bạn. 🤔\n\n"
                    "Bạn có thể cho tôi biết rõ hơn về:\n"
                    "- 📦 **Loại sản phẩm**: áo, quần, đầm, váy...\n"
                    "- 🎯 **Dịp sử dụng**: đi làm, đi chơi, dự tiệc, đi biển...\n"
                    "- 🍂 **Mùa**: xuân, hạ, thu, đông\n"
                    "- 💰 **Ngân sách**: ví dụ dưới 500k\n"
                    "- 🎨 **Màu sắc**: trắng, đen, đỏ...\n\n"
                    "*Ví dụ*: \"Tìm áo sơ mi nam đi làm mùa đông dưới 400k\"")

        response = f"🔍 **Tìm thấy {len(products)} sản phẩm phù hợp:**\n\n"
        for p in products:
            response += self._format_product(p) + "\n\n"

        return response.strip()

    def _response_price_inquiry(self, text):
        product_types = self.extract_product_types(text)
        if product_types:
            products = self.search_products(product_types=product_types, limit=5)
            if products:
                response = f"💰 **Giá các sản phẩm:**\n\n"
                for p in products:
                    response += f"- [{p['id']}] {p['name']}: **{p['price']:,}đ**\n"
                return response

        return ("Bạn muốn hỏi giá sản phẩm nào? Ví dụ:\n"
                "- Áo sơ mi nam bao nhiêu tiền?\n"
                "- Giá đầm dự tiệc?")

    def _response_compare(self, text):
        """So sánh sản phẩm cùng loại"""
        product_types = self.extract_product_types(text)
        if not product_types:
            return ("Để so sánh, bạn cho tôi biết loại sản phẩm nhé.\n"
                    "VD: \"So sánh các áo sơ mi nam\"")

        products = self.search_products(product_types=product_types, limit=3)
        if len(products) < 2:
            return "Cần ít nhất 2 sản phẩm để so sánh."

        response = f"⚖️ **So sánh {len(products)} sản phẩm:**\n\n"
        for i, p in enumerate(products, 1):
            response += f"**{i}. [{p['id']}] {p['name']}**\n"
            response += f"   💰 {p['price']:,}đ | ⭐ {p['rating']}/5 | 🎨 {p['color']}\n"
            response += f"   📏 Size: {', '.join(p['sizes'])}\n"
            response += f"   📝 {p['description']}\n\n"

        # Nhận xét
        cheapest = min(products, key=lambda x: x["price"])
        best_rated = max(products, key=lambda x: x["rating"])
        response += "---\n"
        response += f"💡 **Kết luận:**\n"
        response += f"- 💰 Rẻ nhất: [{cheapest['id']}] {cheapest['name']} ({cheapest['price']:,}đ)\n"
        response += f"- ⭐ Đánh giá cao nhất: [{best_rated['id']}] {best_rated['name']} ({best_rated['rating']}/5)\n"

        return response

    def _response_greeting(self):
        return ("Xin chào! 👋 Tôi là trợ lý tư vấn thời trang.\n\n"
                "Tôi có thể giúp bạn:\n"
                "🧮 **Tư vấn size** — Cho tôi chiều cao, cân nặng\n"
                "👗 **Gợi ý phối đồ** — Cho tôi biết dịp sử dụng\n"
                "🔍 **Tìm sản phẩm** — Theo loại, màu, mùa, ngân sách\n"
                "💰 **Hỏi giá** — Các sản phẩm trong kho\n"
                "⚖️ **So sánh** — Nhiều sản phẩm cùng loại\n\n"
                "Bạn cần gì hôm nay?")

    # ============================================================
    # 8. HÀM CHÍNH
    # ============================================================
    def generate_response(self, user_query: str, chat_history: str = "") -> str:
        text = self._normalize(user_query)

        gender = self.extract_gender(text)
        height = self.extract_height(text)
        weight = self.extract_weight(text)
        occasion = self.extract_occasion(text)
        season = self.extract_season(text)
        budget = self.extract_budget(text)
        product_types = self.extract_product_types(text)

        intent = self.detect_intent(text)

        if intent == 'SIZE_ADVICE':
            return self._response_size_advice(text, gender, height, weight)

        if intent == 'OUTFIT_ADVICE':
            return self._response_outfit_advice(text, gender, occasion)

        if intent == 'PRODUCT_SEARCH':
            return self._response_product_search(
                text, gender, occasion, budget, season, product_types)

        if intent == 'PRICE_INQUIRY':
            return self._response_price_inquiry(text)

        if intent == 'COMPARE':
            return self._response_compare(text)

        if intent == 'GREETING':
            return self._response_greeting()

        return ("Xin lỗi, tôi chưa hiểu rõ câu hỏi của bạn. 🤔\n\n"
                "Bạn có thể hỏi theo các cách sau:\n"
                "- *\"Tôi cao 1m70, nặng 60kg, mặc size gì?\"*\n"
                "- *\"Nam 1m75 muốn mua quần áo mùa đông\"*\n"
                "- *\"Gợi ý đồ đi làm cho nữ\"*\n"
                "- *\"Tìm áo sơ mi nam dưới 400k\"*\n"
                "- *\"So sánh các đầm dự tiệc\"*")

    # ============================================================
    # [ĐÃ COMMENT API] - Đoạn code cũ dùng Gemini
    # Khi nào muốn bật lại thì bỏ comment và đổi tên hàm
    # ============================================================
    #
    # import time
    # from google import genai
    # from config import GEMINI_API_KEY, SYSTEM_PROMPT
    #
    # def generate_response_with_api(self, user_query, chat_history, max_retries=3):
    #     """[API VERSION] Sinh câu trả lời bằng Gemini API"""
    #     client = genai.Client(api_key=GEMINI_API_KEY)
    #     context = f"""
    # --- KHO SẢN PHẨM ({len(self.products)} sản phẩm) ---
    # {json.dumps(self.products, ensure_ascii=False, indent=2)}
    #
    # --- BẢNG QUY ĐỔI SIZE CHUẨN ---
    # {json.dumps(self.size_chart, ensure_ascii=False, indent=2)}
    #
    # --- LUẬT PHỐI ĐỒ ---
    # {json.dumps(self.style_rules, ensure_ascii=False, indent=2)}
    #
    # --- CÁC DỊP SỬ DỤNG PHỔ BIẾN ---
    # {json.dumps(self.occasions, ensure_ascii=False, indent=2)}
    # """
    #     prompt = f"""{SYSTEM_PROMPT}
    # {context}
    # --- LỊCH SỬ TRÒ CHUYỆN ---
    # {chat_history}
    # Người dùng: {user_query}
    # Trợ lý tư vấn:"""
    #     for attempt in range(max_retries):
    #         try:
    #             response = client.models.generate_content(
    #                 model="gemini-2.0-flash",
    #                 contents=prompt
    #             )
    #             return response.text
    #         except Exception as e:
    #             if attempt < max_retries - 1:
    #                 time.sleep(2 ** attempt)
    #                 continue
    #             return f"❌ Có lỗi xảy ra: {str(e)}"