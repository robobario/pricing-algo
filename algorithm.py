#!/usr/bin/env python

import unittest

TRANSPARENCY = "transparency"
DSP = "dsp"
COUNTRY = "country"
ADFORMAT = "adformat"


def specificity(product):
    return len(product["product_features"])


class Model:
    def __init__(self, _model):
        self.model = _model
        self.tiers = {}
        for name, product in model["products"].items():
            tier = specificity(product)
            if tier in self.tiers:
                self.tiers[tier].append(product)
            else:
                self.tiers[tier] = [product]

    def get_tier(self, key):
        return self.tiers[key]

    def get_segment(self, segment_id):
        return self.model["buyer-segments"][segment_id]

    def get_buyer(self, buyer_id):
        return self.model["buyers"][buyer_id]


class Algorithm:
    def __init__(self, model_dict):
        self.model = Model(model_dict)

    def get_price(self, product_features, buyer_features):
        tiers = reversed(sorted(self.model.tiers.keys()))
        for tier in tiers:
            price = self.highest_matching_price_in_tier(self.model.get_tier(tier), product_features, buyer_features)
            if price is not None:
                return price
            else:
                print("found no matching rules with specificity " + str(tier))
        return None

    def highest_matching_price_in_tier(self, products, product_features, buyer_features):
        highest_price = None
        for product in products:
            price = self.highest_matching_price_in_product(product, product_features, buyer_features)
            if highest_price is None or price is not None and price > highest_price:
                highest_price = price
        return highest_price

    def highest_matching_price_in_product(self, product, product_features, buyer_features):
        if not self.product_matches(product, product_features):
            return None
        print("found a rule with product-features [{}] matching impression [{}] ".format(product["product_features"], product_features))
        highest_price = None
        for offer in product["offers"]:
            if self.offer_matches(offer, buyer_features, product_features):
                print("- found an offer with a matching buyer {}".format(str(offer)))
                price = offer["price"]
                if highest_price is None or price is not None and price > highest_price:
                    print("- found a price {} higher than the last max {}".format(str(price), str(highest_price)))
                    highest_price = price
        return highest_price

    def offer_matches(self, offer, buyer_features, product_features):
        if not self.feature_matches_eq(offer, product_features, TRANSPARENCY):
            print("-- offer transparency {} did not match impression transparency {}".format(str(offer[TRANSPARENCY]), buyer_features[TRANSPARENCY]))
            return False
        buyer_groups = [self.model.get_segment(segment) for segment in offer["buyer-segments"]]
        for group in buyer_groups:
            for buyer_id in group:
                buyer = self.model.get_buyer(buyer_id)
                if self.buyer_matches(buyer, buyer_features):
                    print("-- found buyer [{}] matching buyer features [{}]".format(str(buyer), str(buyer_features)))
                    return True
        return False

    def product_matches(self, product, product_features):
        matches = True
        for feature in product["product_features"]:
            feature_type = feature["feature"]
            if feature_type == COUNTRY:
                matches = matches and self.feature_matches_in(feature, product_features, COUNTRY)
            elif feature_type == ADFORMAT:
                matches = matches and self.feature_matches_in(feature, product_features, ADFORMAT)
        return matches

    def feature_matches_in(self, feature, product_features, field):
        if not field in product_features:
            return False
        return product_features[field] in feature["in"]

    def feature_matches_eq(self, feature, product_features, field):
        if not field in product_features:
            return False
        return product_features[field] == feature[field]

    def buyer_matches(self, buyer, buyer_features):
        default = False
        all_matched = True
        for feature in buyer:
            feature_type = feature["feature"]
            if feature_type == DSP:
                all_matched = all_matched and self.feature_matches_in(feature, buyer_features, DSP)
        return default | all_matched


model = {
    "buyers": {
        "Metrigo": [{
            "feature": DSP,
            "in": [1]
        }]
    },
    "buyer-segments": {
        "adwords": ["Metrigo"]
    },
    "products": {
        "rule": {
            "product_features": [
                {
                    "feature": ADFORMAT,
                    "in": ["460x100"]
                }
            ],
            "offers": [{
                "price": 1.3,
                TRANSPARENCY: "blind",
                "buyer-segments": ["adwords"]
            }]
        },
        "rule2": {
            "product_features": [
                {
                    "feature": ADFORMAT,
                    "in": ["460x100"]
                },
                {
                    "feature": COUNTRY,
                    "in": ["DE"]
                }
            ],
            "offers": [{
                "price": 3.4,
                TRANSPARENCY: "blind",
                "buyer-segments": ["adwords"]
            }]
        }
    }
}


class TestAlgorithm(unittest.TestCase):
    def testSimpleCase(self):
        product_features = {ADFORMAT: "460x100", TRANSPARENCY: "blind"}
        buyer_features = {DSP: 1}
        algo = Algorithm(model)
        price = algo.get_price(product_features, buyer_features)
        self.assertEqual(price, 1.3)

    def testProductSpecificity(self):
        product_features = {ADFORMAT: "460x100", TRANSPARENCY: "blind", COUNTRY: "DE"}
        buyer_features = {DSP: 1}
        algo = Algorithm(model)
        price = algo.get_price(product_features, buyer_features)
        self.assertEqual(price, 3.4)


if __name__ == '__main__':
    unittest.main()
