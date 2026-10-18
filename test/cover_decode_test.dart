import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/cover_decode.dart';

void main() {
  test('cover decode follows logical thumbnail dimensions and screen density',
      () {
    expect(seluraCoverDecodePixels(90, 3), 270);
    expect(seluraCoverDecodePixels(128, 2.5), 320);
    expect(seluraCoverDecodePixels(270, 1), 270);
    expect(seluraCoverDecodePixels(0.1, 1), 1);
  });

  test('protects memory against unusually large covers and densities', () {
    expect(seluraCoverDecodePixels(4500, 4), 1536);
    expect(seluraCoverDecodePixels(100, 20), 1536);
    expect(seluraCoverDecodePixels(double.infinity, 3), isNull);
    expect(seluraCoverDecodePixels(double.nan, 3), isNull);
    expect(seluraCoverDecodePixels(0, 3), isNull);
    expect(seluraCoverDecodePixels(-40, 3), isNull);
    expect(seluraCoverDecodePixels(120, 0), isNull);
    expect(seluraCoverDecodePixels(120, double.infinity), isNull);
  });
}
