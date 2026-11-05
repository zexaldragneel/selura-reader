package eu.kanade.presentation.library.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import eu.kanade.tachiyomi.R

@Composable
fun SeirynLibrarySearch(query: String?, onQueryChange: (String?) -> Unit, filtered: Boolean) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (query.isNullOrEmpty()) Text(stringResource(R.string.seiryn_collection), style = MaterialTheme.typography.headlineMedium, fontFamily = FontFamily.Serif)
        OutlinedTextField(
            value = query.orEmpty(),
            onValueChange = { onQueryChange(it.takeIf(String::isNotEmpty)) },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(20.dp),
            singleLine = true,
            label = { Text(stringResource(R.string.seiryn_search_library)) },
            trailingIcon = if (!query.isNullOrEmpty()) {
                { TextButton(onClick = { onQueryChange(null) }) { Text(stringResource(R.string.seiryn_clear)) } }
            } else null,
        )
        if (filtered) Text(stringResource(R.string.seiryn_filters_active), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
    }
}
