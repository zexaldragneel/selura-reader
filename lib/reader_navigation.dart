import 'package:flutter/material.dart';

/// Open the EPUB/PDF page at full opacity from the first frame.
///
/// Decoding a large book may temporarily stall frames on Android. Fading an
/// expensive reader into the bookshelf can freeze halfway through its
/// animation, visually superimposing the bookshelf and reader toolbar/loading
/// text for seconds. Use the reader's branded loading screen instead.
///
/// This changes only presentation; it does not touch book files, progress,
/// bookmarks, narration state or Android app identity.
PageRoute<void> seluraReaderRoute({required Widget child}) =>
    PageRouteBuilder<void>(
      opaque: true,
      transitionDuration: Duration.zero,
      reverseTransitionDuration: Duration.zero,
      pageBuilder: (_, __, ___) => child,
    );
